from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager
from typing import List, Optional

from app.database import get_session, create_tables, AsyncSessionLocal
from app.models import User, Product, Seller, Order
from app.schemas import (
    UserCreate, UserRead, ProductCreate, ProductRead, ProductUpdate,
    SellerCreate, SellerRead, OrderCreate, OrderRead
)
from app.security import get_password_hash, verify_password
from app.jwt_manager import jwt_manager
from app.dependencies import get_current_user, get_current_admin
from app.schemas.auth import Token, LoginRequest, RegisterRequest

from dotenv import load_dotenv
import os

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    
    async with AsyncSessionLocal() as session:
        # СОЗДАНИЕ АДМИНИСТРАТОРА
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                is_admin=True
            )
            session.add(admin_user)
            await session.commit()
            print("\n" + "="*60)
            print("СОЗДАН АДМИНИСТРАТОР ПО УМОЛЧАНИЮ")
            print("Логин: admin@example.com")
            print("Пароль: admin123")
            print("="*60)
        else:
            if not admin_user.is_admin:
                admin_user.is_admin = True
                session.add(admin_user)
                await session.commit()
                print("\n" + "="*60)
                print("ОБНОВЛЕНЫ ПРАВА АДМИНИСТРАТОРА")
                print("is_admin установлен в True")
                print("="*60)
        
        # СОЗДАНИЕ ТЕСТОВЫХ ПРОДАВЦОВ
        default_sellers = [
            {"name": "ElectroTech", "commission_percent": 5.0},
            {"name": "FashionStyle", "commission_percent": 7.5},
            {"name": "HomeGoods", "commission_percent": 4.0},
            {"name": "SportLife", "commission_percent": 6.0},
            {"name": "BookWorld", "commission_percent": 3.5}
        ]
        
        created_sellers_count = 0
        for seller_data in default_sellers:
            result = await session.execute(
                select(Seller).where(Seller.name == seller_data["name"])
            )
            existing_seller = result.scalar_one_or_none()
            
            if not existing_seller:
                seller = Seller(
                    name=seller_data["name"],
                    commission_percent=seller_data["commission_percent"]
                )
                session.add(seller)
                created_sellers_count += 1
        
        if created_sellers_count > 0:
            await session.commit()
            print(f"\nСоздано {created_sellers_count} продавцов по умолчанию")
            
            result = await session.execute(select(Seller))
            sellers = result.scalars().all()
            print("\nДоступные продавцы:")
            for seller in sellers:
                print(f"  - {seller.name} (ID: {seller.id}, комиссия: {seller.commission_percent}%)")
        
        # СОЗДАНИЕ ТЕСТОВЫХ ТОВАРОВ
        result = await session.execute(select(Product))
        existing_products = result.scalars().all()
        
        if not existing_products:
            result = await session.execute(select(Seller.id).limit(1))
            first_seller_id = result.scalar()
            
            if first_seller_id:
                test_products = [
                    {"name": "Смартфон Samsung Galaxy", "price": 29999.99, "seller_id": first_seller_id},
                    {"name": "Ноутбук Lenovo IdeaPad", "price": 54999.99, "seller_id": first_seller_id},
                    {"name": "Наушники Sony WH-1000XM4", "price": 19999.99, "seller_id": first_seller_id}
                ]
                
                for product_data in test_products:
                    product = Product(
                        name=product_data["name"],
                        price=product_data["price"],
                        seller_id=product_data["seller_id"]
                    )
                    session.add(product)
                
                await session.commit()
                print("\nСозданы тестовые товары для демонстрации")
    
    yield

app = FastAPI(
    title="Marketplace API",
    description="API для маркетплейса с несколькими продавцами",
    version="1.0.0",
    lifespan=lifespan
)

# АУТЕНТИФИКАЦИЯ
@app.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED,
          summary="Регистрация пользователя",
          description="Создание нового пользователя в системе")
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
        hashed_password=get_password_hash(user_data.password),
        is_admin=False
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user

@app.post("/login", response_model=Token,
          summary="Вход в систему",
          description="Аутентификация пользователя и получение JWT токена")
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
    
    print(f"DEBUG: User {user.username} is_admin = {user.is_admin}")
    
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin
    }
    
    access_token = jwt_manager.create_access_token(data=token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/me", response_model=UserRead,
         summary="Информация о текущем пользователе",
         description="Получение информации о текущем аутентифицированном пользователе")
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

# PRODUCT
@app.get("/products", response_model=List[ProductRead],
         summary="Получить список товаров",
         description="Возвращает список всех товаров с пагинацией. Доступно всем.")
async def get_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(
        select(Product).offset(skip).limit(limit)
    )
    products = result.scalars().all()
    return products

@app.get("/products/{product_id}", response_model=ProductRead,
         summary="Получить товар по ID",
         description="Возвращает информацию о конкретном товаре. Доступно всем.")
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    return product

@app.post("/products", response_model=ProductRead,
          status_code=status.HTTP_201_CREATED,
          summary="Создать новый товар",
          description="Создание нового товара. Требуются права администратора.")
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_session),
    admin_data: dict = Depends(get_current_admin)
):
    result = await db.execute(
        select(Seller).where(Seller.id == product_data.seller_id)
    )
    seller = result.scalar_one_or_none()
    
    if seller is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанный продавец не существует"
        )
    
    if product_data.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Цена должна быть положительным числом"
        )
    
    product = Product(
        name=product_data.name,
        price=product_data.price,
        seller_id=product_data.seller_id
    )
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return product

@app.put("/products/{product_id}", response_model=ProductRead,
         summary="Обновить товар",
         description="Обновление информации о товаре. Требуются права администратора.")
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_session),
    admin_data: dict = Depends(get_current_admin)
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    if product_data.seller_id is not None:
        result = await db.execute(
            select(Seller).where(Seller.id == product_data.seller_id)
        )
        seller = result.scalar_one_or_none()
        
        if seller is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указанный продавец не существует"
            )
    
    if product_data.price is not None and product_data.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Цена должна быть положительным числом"
        )
    
    update_data = product_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    await db.commit()
    await db.refresh(product)
    
    return product

@app.delete("/products/{product_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Удалить товар",
            description="Удаление товара. Требуются права администратора.")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_session),
    admin_data: dict = Depends(get_current_admin)
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    await db.delete(product)
    await db.commit()
    
    return None

# SELLER

@app.get("/sellers", response_model=List[SellerRead],
         summary="Получить список продавцов",
         description="Возвращает список всех продавцов с их комиссиями")
async def get_sellers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(
        select(Seller).offset(skip).limit(limit)
    )
    sellers = result.scalars().all()
    return sellers

@app.get("/sellers/{seller_id}", response_model=SellerRead,
         summary="Получить продавца по ID",
         description="Возвращает информацию о конкретном продавце")
async def get_seller(
    seller_id: int,
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(
        select(Seller).where(Seller.id == seller_id)
    )
    seller = result.scalar_one_or_none()
    
    if seller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продавец не найден"
        )
    
    return seller

@app.post("/sellers", response_model=SellerRead,
          status_code=status.HTTP_201_CREATED,
          summary="Создать продавца",
          description="Создание нового продавца. Требуются права администратора.")
async def create_seller(
    seller_data: SellerCreate,
    db: AsyncSession = Depends(get_session),
    admin_data: dict = Depends(get_current_admin)
):
    if not 0 <= seller_data.commission_percent <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Комиссия должна быть от 0 до 100 процентов"
        )
    
    seller = Seller(
        name=seller_data.name,
        commission_percent=seller_data.commission_percent
    )
    
    db.add(seller)
    await db.commit()
    await db.refresh(seller)
    
    return seller

@app.delete("/sellers/{sellers_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Удалить продавца",
            description="Удаление продавца. Требуются права администратора.")
async def delete_seller(
    seller_id: int,
    db: AsyncSession = Depends(get_session),
    admin_data: dict = Depends(get_current_admin)
):
    result = await db.execute(
        select(Seller).where(Seller.id == seller_id)
    )
    seller = result.scalar_one_or_none()
    
    if seller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продавец не найден"
        )
    
    await db.delete(seller)
    await db.commit()
    
    return None

# ORDER

@app.get("/orders", response_model=List[OrderRead],
         summary="Получить список заказов",
         description="Возвращает список всех заказов (Требуются права администратора)")
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
    admin_data: dict = Depends(get_current_admin)
):
    result = await db.execute(
        select(Order).offset(skip).limit(limit)
    )
    orders = result.scalars().all()
    return orders

@app.get("/orders/{order_id}", response_model=OrderRead,
         summary="Получить заказ по id",
         description="Возвращает конкретный заказ по id (Требуются права администратора)"
         )
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
    admin_data: dict = Depends(get_current_admin)
):
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден"
        )

    return order

@app.post("/orders", response_model=OrderRead,
          summary="Создать заказ",
          description="Создаёт новый заказ")
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user)
):
    result = await db.execute(
        select(Product).where(Product.id == order_data.product_id)
    )
    product = result.scalar_one_or_none()
    
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанный продукт не существует"
        )
    
    if order_data.count <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Число должно быть больше 0"
        )
    
    order = Order(
        user_id=current_user_id,
        product_id=order_data.product_id,
        count=order_data.count       
    )
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    return order

@app.get("/my-orders", response_model=List[OrderRead],
         summary="Получить мои заказы",
         description="Возвращает список заказов текущего пользователя")
async def get_my_orders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user)
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user_id).offset(skip).limit(limit)
    )
    orders = result.scalars().all()
    return orders

@app.delete("/orders/{order_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Удалить заказ",
            description="Удаление заказа текущего пользователя")
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user)
):
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == current_user_id
        )
    )
    order = result.scalar_one_or_none()
    
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден или нет доступа"
        )
    
    await db.delete(order)
    await db.commit()
    
    return None
    


# ВЕБ-СТРАНИЦЫ

@app.get("/", response_class=HTMLResponse,
         summary="Главная страница",
         description="Домашняя страница API маркетплейса")
async def home_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Marketplace API</title>
        <style>
            body { font-family: Arial; margin: auto; padding: 20px; max-width: 800px; }
            h1 { text-align: center; }
            .menu { margin: 20px 0; }
            .menu a { 
                display: inline-block; 
                padding: 10px; 
                background: #4CAF50; 
                color: white; 
                text-decoration: none; 
                margin: 5px;
            }
        </style>
    </head>
    <body>
        <h1>Marketplace API</h1>
        <div class="menu">
            <a href="/register-page">Регистрация</a>
            <a href="/login-page">Вход</a>
            <a href="/me-page">Личный кабинет</a>
            <a href="/docs" target="_blank">Документация API</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/login-page", response_class=HTMLResponse)
async def login_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Вход</title>
        <style>
            body { font-family: Arial; margin: auto; padding: 20px; max-width: 400px; }
            form { margin: 20px 0; }
            input, button { 
                width: 100%; 
                padding: 8px; 
                margin: 5px 0; 
            }
            button { background: #4CAF50; color: white; border: none; }
            .message { margin: 10px 0; padding: 10px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .link { margin-top: 10px; }
        </style>
    </head>
    <body>
        <h2>Вход</h2>
        <form id="loginForm">
            <input type="email" id="email" placeholder="Email" required>
            <input type="password" id="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
            <h1>Для входа как админ:</h1>
            <h3>Логин: admin@example.com</h3>
            <h3>Пароль: admin123</h3>
        </form>
        <div id="message"></div>
        <div class="link">
            <a href="/register-page">Нет аккаунта? Зарегистрируйтесь</a>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email: email, password: password})
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
                    resultDiv.innerHTML = 'Вы уже вошли в систему!<br><a href="/me-page">Личный кабинет</a>';
                }
            });
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
        <title>Регистрация</title>
        <style>
            body { font-family: Arial; margin: auto; padding: 20px; max-width: 400px; }
            form { margin: 20px 0; }
            input, button { 
                width: 100%; 
                padding: 8px; 
                margin: 5px 0; 
            }
            button { background: #4CAF50; color: white; border: none; }
            .message { margin: 10px 0; padding: 10px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .link { margin-top: 10px; }
            .small { font-size: 12px; color: #666; }
        </style>
    </head>
    <body>
        <h2>Регистрация</h2>
        <form id="registerForm">
            <input type="text" id="username" placeholder="Имя пользователя" required>
            <div class="small">Минимум 3 символа, только буквы, цифры и _</div>
            <input type="email" id="email" placeholder="Email" required>
            <input type="password" id="password" placeholder="Пароль" required>
            <div class="small">Минимум 8 символов, цифра и буква</div>
            <button type="submit">Зарегистрироваться</button>
        </form>
        <div id="message"></div>
        <div class="link">
            <a href="/login-page">Уже есть аккаунт? Войдите</a>
        </div>
        
        <script>
            document.getElementById('registerForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: username, email: email, password: password})
                });
                
                const resultDiv = document.getElementById('message');
                resultDiv.className = 'message';
                
                if (response.ok) {
                    resultDiv.className = 'message success';
                    resultDiv.innerHTML = 'Регистрация успешна! Переход на страницу входа...';
                    setTimeout(() => window.location.href = '/login-page', 2000);
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
            body { font-family: Arial; margin: auto; padding: 20px; max-width: 600px; }
            .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
            button { 
                padding: 8px; 
                margin: 5px; 
                background: #4CAF50; 
                color: white; 
                border: none; 
            }
            .admin-btn { background: #5c7fdf; }
            textarea { width: 100%; height: 80px; padding: 8px; }
            .message { margin: 10px 0; padding: 10px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .info { margin: 5px 0; padding: 8px; background: #f0f0f0; }
        </style>
    </head>
    <body>
        <h2>Личный кабинет</h2>
        
        <div class="section">
            <h3>Информация о пользователе:</h3>
            <div id="userData"></div>
        </div>
        
        <div class="section">
            <h3>JWT токен:</h3>
            <textarea id="tokenDisplay" readonly></textarea>
            <div>
                <button onclick="copyToken()">Скопировать токен</button>
                <button onclick="loadUserData()">Обновить данные</button>
            </div>
        </div>
        
        <div>
            <button onclick="window.location.href='/'">На главную</button>
            <button onclick="logout()">Выйти</button>
            <button id="mainButton" style="display:none;"
                    onclick="window.location.href='/main'">Функционал</button>
        </div>
        
        <div id="message"></div>
        
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const userToken = localStorage.getItem('marketplace_token');
                if (userToken) {
                    document.getElementById('tokenDisplay').value = userToken;
                    loadUserData();
                } else {
                    document.getElementById('userData').innerHTML = '<div class="error">Токен не найден. Войдите в систему.</div>';
                }
            });
            
            async function loadUserData() {
                const token = localStorage.getItem('marketplace_token');
                if (!token) {
                    showMessage('Токен не найден', 'error');
                    return;
                }
                
                try {
                    const response = await fetch('/me', {
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                    
                    if (response.ok) {
                        const user = await response.json();
                        document.getElementById('userData').innerHTML = `
                            <div class="info">ID: ${user.id}</div>
                            <div class="info">Имя: ${user.username}</div>
                            <div class="info">Email: ${user.email}</div>
                            <div class="info">Админ: ${user.is_admin ? 'Да' : 'Нет'}</div>
                        `;
                        document.getElementById('mainButton').style.display = 'inline-block';
                        showMessage('Данные обновлены', 'success');
                    } else {
                        const error = await response.json();
                        showMessage('Ошибка: ' + error.detail, 'error');
                        
                        if (response.status === 401) {
                            localStorage.removeItem('marketplace_token');
                            setTimeout(() => window.location.href = '/login-page', 2000);
                        }
                    }
                } catch (error) {
                    showMessage('Ошибка сети', 'error');
                }
            }
            
            function copyToken() {
                const token = document.getElementById('tokenDisplay').value;
                if (token) {
                    navigator.clipboard.writeText(token);
                    showMessage('Токен скопирован!', 'success');
                }
            }
            
            function showMessage(text, type) {
                const messageDiv = document.getElementById('message');
                messageDiv.textContent = text;
                messageDiv.className = 'message ' + type;
                setTimeout(() => messageDiv.className = 'message', 3000);
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

@app.get("/main", response_class=HTMLResponse)
async def main_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Главная - Marketplace</title>
        <style>
            body { font-family: Arial; margin: auto; padding: 20px; max-width: 800px; }
            .menu { margin: 20px 0; }
            .menu a { 
                display: inline-block; 
                padding: 10px; 
                background: #4CAF50; 
                color: white; 
                text-decoration: none; 
                margin: 5px;
            }
            .card { 
                border: 1px solid #ddd; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px;
            }
            .admin-only { color: #dc3545; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Добро пожаловать в Marketplace!</h1>
        
        <div class="menu">
            <h3>Доступные действия:</h3>
            <a href="/products" target="_blank">Просмотреть товары</a>
            <a href="/docs" target="_blank">Документация API</a>
            <a href="/me-page">Личный кабинет</a>
        </div>
        
        <div class="card">
            <h3>Система прав доступа:</h3>
            <ul>
                <li><strong>Все пользователи:</strong>
                    <ul>
                        <li>Просмотр товаров (GET /products)</li>
                        <li>Просмотр продавцов (GET /sellers)</li>
                        <li>Регистрация и вход</li>
                    </ul>
                </li>
                <li><strong>Аутентифицированные пользователи:</strong>
                    <ul>
                        <li>Создание заказов (POST /orders)</li>
                        <li>Просмотр своих заказов (GET /orders)</li>
                    </ul>
                </li>
                <li class="admin-only"><strong>Только администраторы:</strong>
                    <ul>
                        <li>Создание товаров (POST /products)</li>
                        <li>Обновление товаров (PUT /products/{id})</li>
                        <li>Удаление товаров (DELETE /products/{id})</li>
                        <li>Создание продавцов (POST /sellers)</li>
                    </ul>
                </li>
            </ul>
        </div>
        
        <div class="card">
            <h3>Доступные эндпоинты API:</h3>
            <ul>
                <li><strong>GET /products</strong> - список товаров <em>(всем)</em></li>
                <li><strong>GET /products/{id}</strong> - товар по ID <em>(всем)</em></li>
                <li class="admin-only"><strong>POST /products</strong> - создать товар <em>(только админы)</em></li>
                <li class="admin-only"><strong>PUT /products/{id}</strong> - обновить товар <em>(только админы)</em></li>
                <li class="admin-only"><strong>DELETE /products/{id}</strong> - удалить товар <em>(только админы)</em></li>
                <li><strong>GET /sellers</strong> - список продавцов <em>(всем)</em></li>
                <li><strong>GET /sellers/{id}</strong> - продавец по ID <em>(всем)</em></li>
                <li class="admin-only"><strong>POST /sellers</strong> - создать продавца <em>(только админы)</em></li>
                <li><strong>GET /orders</strong> - мои заказы <em>(только аутентифицированные)</em></li>
                <li><strong>POST /orders</strong> - создать заказ <em>(только аутентифицированные)</em></li>
            </ul>
        </div>
        
        <button onclick="window.location.href='/'">На главную страницу</button>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)