🏠 Broker Project Backend
FastAPI • PostgreSQL • Clean Architecture • JWT Auth • Alembic

A production-style backend system for a property brokerage platform built using FastAPI and PostgreSQL, designed with service separation, role-based authentication, and scalable architecture principles.

This project demonstrates backend engineering fundamentals including API design, database modeling, authentication, migration management, and business logic isolation.

🚀 Core Capabilities

🔐 Authentication & Authorization

-JWT-based authentication
-Token expiration handling
-Role-based separation (Customer / Agent)
-Secure password hashing

🏘 Property Management

-Property creation & listing
-Ownership-based access control
-Availability tracking

💰 Bidding & Deal System

-Bid placement logic
-Status-based deal lifecycle
-Unique constraint enforcement (interest)
-Commission-based pricing logic

🧠 Agent Commission Engine

-Centralized agent service
-Configurable fee percentage
-Isolated pricing logic (service layer abstraction)

🏗 Architecture Overview

The project follows a layered backend architecture:

                   Client
                     ↓
               Routers (API Layer)
                     ↓
            Services (Business Logic Layer)
                     ↓
                Models (ORM Layer)
                     ↓
               PostgreSQL Database

Why this structure?

-Routers → Handle HTTP layer only

-Services → Contain core business logic

-Models → Database structure

-Schemas → Request/Response validation

-Config → Environment-based settings

-Alembic → Version-controlled schema evolution

This separation ensures:

1.Scalability

2.Clean testing boundaries

3.Business logic isolation

4.Maintainability

🛠 Technology Stack
-Layer	Technology
-API Framework	FastAPI
-Database	PostgreSQL
-ORM	SQLAlchemy
-Migrations	Alembic
-Auth	JWT
-Validation	Pydantic
-Server	Uvicorn
📂 Project Structure
backend/
│
├── routers/          # API endpoints
           |── auth.py
           |── bid.py
           |── property.py
           |── user.py
├── services/         # Business logic
           |── agent.py
           |── deal.py
           |── pricing.py
├── schemas/          # Request/response validation
           |── bid.py
           |── property.py
           |── user.py
├── models.py         # Database models
├── database.py       # DB connection setup
├── config.py         # Environment configuration
└── main.py           # Application entrypoint

alembic/
└── versions/         # Migration history

⚙️ Setup Guide
1️⃣ Clone Repository
git clone https://github.com/Priyamvada4627/Broker-Project.git
cd Broker-Project

2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Configure Environment Variables

Create a .env file:

DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_password
DATABASE_NAME=your_database
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30


⚠️ .env is excluded via .gitignore.

5️⃣ Apply Migrations
alembic upgrade head

6️⃣ Run Application
uvicorn backend.main:app --reload


API Docs:

http://127.0.0.1:8000/docs

📊 Database Design Thinking

-Separate Agent entity for commission control

-Unique constraints to prevent duplicate deals

-Foreign-key relationships for ownership integrity

-Migration-based schema control for version safety

-Alembic ensures:

-Schema reproducibility

-Controlled upgrades/downgrades

-Production-ready migration workflow

🔎 Engineering Highlights

-Clean separation between business logic and routing

-Config-driven environment management

-Scalable service layer pattern

-JWT authentication best practices

-Database constraints to enforce business rules

-Migration-first database evolution

📈 Future Improvements

-Multi-agent support

-Redis caching layer

-Dockerized deployment

-CI/CD pipeline integration

-Unit & integration test coverage

-Async database optimization

👩‍💻 Author

Priyamvada Singh
Backend Developer | Engineering Student
GitHub: https://github.com/Priyamvada4627

