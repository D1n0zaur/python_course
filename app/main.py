from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager

from app.database import get_session, create_tables
from app.models import User, Product, Seller
from app.schemas import UserCreate, UserRead, ProductCreate, ProductRead, SellerCreate, SellerRead
from app.security import get_password_hash, verify_password
from app.jwt_manager import jwt_manager
from app.dependencies import get_current_user
from app.schemas.auth import Token, LoginRequest, RegisterRequest

from dotenv import load_dotenv
import os

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def home_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Marketplace - Главная</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                text-align: center;
                margin-bottom: 40px;
                background-color: #4CAF50;
                color: white;
                padding: 30px;
                border-radius: 10px;
            }
            .nav-cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
            }
            .card {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
                transition: transform 0.3s;
            }
            .card:hover {
                transform: translateY(-5px);
            }
            .card h3 {
                color: #333;
                margin-bottom: 15px;
            }
            .card p {
                color: #666;
                margin-bottom: 20px;
            }
            .card button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            .card button:hover {
                background-color: #45a049;
            }
            .api-info {
                margin-top: 40px;
                background-color: white;
                padding: 20px;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛒 Marketplace API</h1>
            <p>Платформа для продавцов и покупателей</p>
        </div>
        
        <div class="nav-cards">
            <div class="card">
                <h3>🔐 Регистрация</h3>
                <p>Создайте новый аккаунт для доступа ко всем функциям маркетплейса</p>
                <button onclick="window.location.href='/register-page'">Зарегистрироваться</button>
            </div>
            
            <div class="card">
                <h3>🚪 Вход</h3>
                <p>Войдите в свой аккаунт, чтобы управлять товарами и заказами</p>
                <button onclick="window.location.href='/login-page'">Войти</button>
            </div>
            
            <div class="card">
                <h3>👤 Личный кабинет</h3>
                <p>Просмотр и управление вашим профилем и токеном доступа</p>
                <button onclick="window.location.href='/me-page'">Перейти</button>
            </div>
            
            <div class="card">
                <h3>📦 Товары</h3>
                <p>Просмотр каталога товаров и создание новых объявлений</p>
                <button onclick="window.location.href='/products'">Смотреть товары</button>
            </div>
        </div>
        
        <div class="api-info">
            <h3>📚 API Документация</h3>
            <p>Полная документация API доступна по ссылкам:</p>
            <ul>
                <li><a href="/docs" target="_blank">Swagger UI документация</a></li>
                <li><a href="/redoc" target="_blank">ReDoc документация</a></li>
            </ul>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user_email = result.scalar_one_or_none()
    
    if existing_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_user_username = result.scalar_one_or_none()
    
    if existing_user_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user

@app.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {"sub": str(user.id), "username": user.username}
    access_token = jwt_manager.create_access_token(data=token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return user

@app.get("/login-page", response_class=HTMLResponse)
async def login_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Вход в Marketplace</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 400px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .form-container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h2 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                color: #555;
                font-weight: bold;
            }
            input {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                width: 100%;
                padding: 12px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            button:hover {
                background-color: #45a049;
            }
            .message {
                padding: 10px;
                border-radius: 5px;
                margin-top: 20px;
                text-align: center;
            }
            .success {
                background-color: #d4edda;
                color: #155724;
            }
            .error {
                background-color: #f8d7da;
                color: #721c24;
            }
            .link {
                text-align: center;
                margin-top: 20px;
            }
            .link a {
                color: #4CAF50;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h2>Вход в систему</h2>
            <form id="loginForm">
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="form-group">
                    <label for="password">Пароль:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit">Войти</button>
            </form>
            <div id="message"></div>
            <div class="link">
                <a href="/register-page">Нет аккаунта? Зарегистрируйтесь</a>
            </div>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: email,
                        password: password
                    })
                });
                
                const resultDiv = document.getElementById('message');
                resultDiv.className = 'message';
                
                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('marketplace_token', data.access_token);
                    window.location.href = '/me-page';
                } else {
                    const error = await response.json();
                    resultDiv.className = 'message error';
                    resultDiv.textContent = 'Ошибка: ' + error.detail;
                }
            });
            
            document.addEventListener('DOMContentLoaded', function() {
                const token = localStorage.getItem('marketplace_token');
                if (token) {
                    const resultDiv = document.getElementById('message');
                    resultDiv.className = 'message success';
                    resultDiv.innerHTML = `
                        Вы уже вошли в систему!<br>
                        <a href="/me-page">Перейти в личный кабинет</a>
                        <br>
                        <button onclick="logout()">Выйти</button>
                    `;
                }
            });
            
            function logout() {
                localStorage.removeItem('marketplace_token');
                window.location.reload();
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/register-page", response_class=HTMLResponse)
async def register_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Регистрация в Marketplace</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 400px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .form-container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h2 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                color: #555;
                font-weight: bold;
            }
            input {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                width: 100%;
                padding: 12px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            button:hover {
                background-color: #45a049;
            }
            .message {
                padding: 10px;
                border-radius: 5px;
                margin-top: 20px;
                text-align: center;
            }
            .success {
                background-color: #d4edda;
                color: #155724;
            }
            .error {
                background-color: #f8d7da;
                color: #721c24;
            }
            .link {
                text-align: center;
                margin-top: 20px;
            }
            .link a {
                color: #4CAF50;
                text-decoration: none;
            }
            .requirements {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h2>Регистрация</h2>
            <form id="registerForm">
                <div class="form-group">
                    <label for="username">Имя пользователя:</label>
                    <input type="text" id="username" name="username" required>
                    <div class="requirements">Минимум 3 символа, только буквы, цифры и подчеркивание</div>
                </div>
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="form-group">
                    <label for="password">Пароль:</label>
                    <input type="password" id="password" name="password" required>
                    <div class="requirements">Минимум 8 символов, хотя бы одна цифра и одна буква</div>
                </div>
                <button type="submit">Зарегистрироваться</button>
            </form>
            <div id="message"></div>
            <div class="link">
                <a href="/login-page">Уже есть аккаунт? Войдите</a>
            </div>
        </div>
        
        <script>
            document.getElementById('registerForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: username,
                        email: email,
                        password: password
                    })
                });
                
                const resultDiv = document.getElementById('message');
                resultDiv.className = 'message';
                
                if (response.ok) {
                    resultDiv.className = 'message success';
                    resultDiv.innerHTML = 'Регистрация успешна! Перенаправление на страницу входа...';
                    setTimeout(() => {
                        window.location.href = '/login-page';
                    }, 2000);
                } else {
                    const error = await response.json();
                    resultDiv.className = 'message error';
                    resultDiv.textContent = 'Ошибка: ' + error.detail;
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/me-page", response_class=HTMLResponse)
async def me_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Личный кабинет</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h2 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .user-info {
                background-color: #f9f9f9;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .info-item {
                margin-bottom: 10px;
                padding: 10px;
                background-color: white;
                border-left: 4px solid #4CAF50;
            }
            .token-section {
                margin-top: 20px;
            }
            textarea {
                width: 100%;
                height: 100px;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-family: monospace;
                margin-bottom: 10px;
            }
            .buttons {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            button {
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                flex: 1;
            }
            .primary-btn {
                background-color: #4CAF50;
                color: white;
            }
            .secondary-btn {
                background-color: #f0f0f0;
                color: #333;
            }
            button:hover {
                opacity: 0.9;
            }
            .message {
                padding: 10px;
                border-radius: 5px;
                margin-top: 20px;
                text-align: center;
                display: none;
            }
            .success {
                background-color: #d4edda;
                color: #155724;
                display: block;
            }
            .error {
                background-color: #f8d7da;
                color: #721c24;
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Личный кабинет</h2>
            
            <div class="user-info">
                <h3>Информация о пользователе:</h3>
                <div id="userData"></div>
            </div>
            
            <div class="token-section">
                <h3>Ваш JWT токен:</h3>
                <textarea id="tokenDisplay" readonly></textarea>
                <div class="buttons">
                    <button class="primary-btn" onclick="copyToken()">Скопировать токен</button>
                    <button class="secondary-btn" onclick="loadUserData()">Обновить данные</button>
                </div>
            </div>
            
            <div class="buttons">
                <button class="primary-btn" onclick="goToProducts()">Смотреть товары</button>
                <button class="secondary-btn" onclick="logout()">Выйти</button>
            </div>
            
            <div id="message"></div>
        </div>
        
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const userToken = localStorage.getItem('marketplace_token');
                if (userToken) {
                    document.getElementById('tokenDisplay').value = userToken;
                    loadUserData();
                } else {
                    document.getElementById('userData').innerHTML = `
                        <div class="info-item error">
                            Токен не найден. Пожалуйста, войдите в систему.
                        </div>
                        <br>
                        <button class="primary-btn" onclick="window.location.href='/login-page'">Войти</button>
                    `;
                }
            });
            
            async function loadUserData() {
                const token = localStorage.getItem('marketplace_token');
                if (!token) {
                    showMessage('Ошибка: токен не найден', 'error');
                    return;
                }
                
                try {
                    const response = await fetch('/me', {
                        headers: {
                            'Authorization': 'Bearer ' + token
                        }
                    });
                    
                    if (response.ok) {
                        const user = await response.json();
                        document.getElementById('userData').innerHTML = `
                            <div class="info-item">
                                <strong>ID:</strong> ${user.id}
                            </div>
                            <div class="info-item">
                                <strong>Имя пользователя:</strong> ${user.username}
                            </div>
                            <div class="info-item">
                                <strong>Email:</strong> ${user.email}
                            </div>
                        `;
                        showMessage('Данные обновлены', 'success');
                    } else {
                        const error = await response.json();
                        showMessage('Ошибка: ' + error.detail, 'error');
                        
                        if (response.status === 401) {
                            localStorage.removeItem('marketplace_token');
                            setTimeout(() => {
                                window.location.href = '/login-page';
                            }, 2000);
                        }
                    }
                } catch (error) {
                    showMessage('Ошибка сети', 'error');
                }
            }
            
            function copyToken() {
                const token = document.getElementById('tokenDisplay').value;
                if (token) {
                    navigator.clipboard.writeText(token).then(() => {
                        showMessage('Токен скопирован в буфер обмена!', 'success');
                    });
                }
            }
            
            function showMessage(text, type) {
                const messageDiv = document.getElementById('message');
                messageDiv.textContent = text;
                messageDiv.className = 'message ' + type;
                setTimeout(() => {
                    messageDiv.className = 'message';
                }, 3000);
            }
            
            function goToProducts() {
                window.location.href = '/products';
            }
            
            function logout() {
                localStorage.removeItem('marketplace_token');
                window.location.href = '/login-page';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)