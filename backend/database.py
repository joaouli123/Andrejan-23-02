from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from models import Base, User, Brand
from config import get_settings
from security import get_password_hash
import os

settings = get_settings()

# Convert sqlite:/// to sqlite+aiosqlite:///
db_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create tables and seed admin user + default brands"""
    # Ensure data dir exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.images_dir, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create admin user if not exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == settings.admin_email))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                email=settings.admin_email,
                full_name="Administrador",
                hashed_password=get_password_hash(settings.admin_password),
                is_admin=True,
            )
            session.add(admin)

        # Seed 15 default elevator brands
        default_brands = [
            ("otis", "Otis"),
            ("schindler", "Schindler"),
            ("thyssenkrupp", "ThyssenKrupp"),
            ("kone", "KONE"),
            ("mitsubishi", "Mitsubishi Electric"),
            ("fujitec", "Fujitec"),
            ("hyundai", "Hyundai Elevator"),
            ("lg", "LG Otis"),
            ("toshiba", "Toshiba Elevator"),
            ("hitachi", "Hitachi"),
            ("atlas", "Atlas Schindler"),
            ("elevadores-brasil", "Elevadores Brasil"),
            ("engetec", "Engetec"),
            ("villarta", "Villarta"),
            ("other", "Outras Marcas"),
        ]

        for slug, name in default_brands:
            result = await session.execute(select(Brand).where(Brand.slug == slug))
            brand = result.scalar_one_or_none()
            if not brand:
                session.add(Brand(slug=slug, name=name))

        await session.commit()
