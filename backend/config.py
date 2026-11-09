from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_hostname: str = "localhost"
    database_port: str = "5432"
    database_password: str = "postgres"
    database_name: str = "broker_db"
    database_username: str = "postgres"
    secret_key: str = "default_secret_key_for_development_only_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cloudinary_cloud_name: str = "test_cloud"
    cloudinary_api_key: str = "test_key"
    cloudinary_api_secret: str = "test_secret"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
