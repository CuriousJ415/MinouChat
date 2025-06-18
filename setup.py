from setuptools import setup, find_packages

setup(
    name="miachat",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi",
        "uvicorn",
        "jinja2",
        "python-multipart",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "sqlalchemy",
        "alembic",
        "python-dotenv",
    ],
    python_requires=">=3.8",
) 