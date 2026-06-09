from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password:str
    database_name:str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret:str
    model_config = {
        "env_file": ".env",
       
    }
    

settings=Settings()

