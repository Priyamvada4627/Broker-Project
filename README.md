🏠 Broker Project
A production-style property brokerage backend built with FastAPI and PostgreSQL, featuring a complete interest-to-deal lifecycle, agent assignment, document verification, ML-based price estimation, and role-based access control.
🔗 Live API: https://broker-project-2.onrender.com/docs

🚀 Tech Stack
LayerTechnologyAPI FrameworkFastAPIDatabasePostgreSQLORMSQLAlchemyMigrationsAlembicAuthJWT (python-jose)ValidationPydantic V2ServerUvicornSchedulerAPSchedulerFile StorageCloudinaryMLscikit-learn (joblib models)

⚙️ Setup
1. Clone the repository
bashgit clone https://github.com/Priyamvada4627/Broker-Project.git
cd Broker-Project
2. Create and activate virtual environment
bashpython -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
3. Install dependencies
bashpip install -r requirements.txt
4. Configure environment variables
Create a .env file in the project root:
envDATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_password
DATABASE_NAME=your_database
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
5. Apply migrations
bashalembic upgrade head
6. Seed the default agent
Run the seed script to create the default platform agent:
bashpython -m backend.seed
This creates:

User: agent@platform.com / password: securepassword
Default agent with fee_percent=2.0, min_fee=1000, max_fee=50000

7. Run the server
bashuvicorn backend.main:app --reload
API docs: http://127.0.0.1:8000/docs

🏗️ Architecture
Client
  ↓
Routers (API Layer)       — HTTP handling, request validation
  ↓
Services (Business Logic) — pricing, deal creation, agent assignment, ML, Cloudinary
  ↓
Models (ORM Layer)        — SQLAlchemy models
  ↓
PostgreSQL Database

📂 Project Structure
backend/
├── routers/
│   ├── auth.py          # Login
│   ├── user.py          # Registration, profile
│   ├── property.py      # Property CRUD + update + delete
│   ├── bid.py           # Interest & negotiation
│   ├── deal.py          # Deal retrieval, payment, completion
│   ├── document.py      # Document upload (Cloudinary) & verification
│   ├── agent.py         # Agent registration, property verification, dashboard
│   └── ml.py            # Standalone ML price estimate endpoint
├── services/
│   ├── agent.py         # Agent assignment with load balancing
│   ├── deal.py          # Deal creation logic
│   ├── pricing.py       # Fee computation
│   ├── cloudinary_service.py  # Cloudinary upload/delete helpers
│   └── ml.py            # Model loading and price prediction
├── schemas/
│   ├── user.py
│   ├── Property.py
│   ├── bid.py
│   └── deal.py
├── scripts/
│   └── train_model.py   # ML model training script
├── models_store/
│   ├── price_model_buy.joblib
│   └── price_model_rent.joblib
├── models.py            # All database models
├── database.py          # DB connection
├── oauth2.py            # JWT auth + role guards
├── utils.py             # Password hashing
├── config.py            # Environment config
├── seed.py              # Default agent seeder
└── main.py              # App entrypoint + scheduler

🔄 System Flow
Property Verification Cycle
Seller posts property
        ↓
System sets verification_deadline = now + 10 days
        ↓
Agent reviews property (assigned agent only)
        ↓
Agent: verified → property is live
Agent: changes_required → seller gets remarks, deadline resets to 5 days on re-submission
        ↓
If not verified before deadline → auto deleted by scheduler
Interest Cycle
Buyer creates interest on a listed property
        ↓
Seller: accept_bid | counter | reject
        ↓
Buyer: accept_counter | reject_counter | withdraw
        ↓
Deal auto-created when interest is accepted / agreed
All other interests on that property → rejected
Property marked unavailable
Deal Cycle
Deal created
        ↓
Buyer & Seller upload documents (via Cloudinary)
        ↓
Agent verifies each document → verified | rejected
        ↓
If rejected → party gets rejection notes + 7 days to re-upload
If not re-uploaded in 7 days → deal cancelled by scheduler
        ↓
All documents verified → deal status: documents_verified
        ↓
Buyer confirms payment → deal status: payment_pending
        ↓
Agent marks deal complete → deal status: completed

📌 API Endpoints
Auth
MethodEndpointDescriptionPOST/loginGet JWT token
Users
MethodEndpointDescriptionPOST/users/registerRegister as customerGET/users/meGet own profile
Agents
MethodEndpointDescriptionPOST/agents/registerCreate new agent (agent only)PATCH/agents/verify/property/{id}?action=verifiedVerify a property listingPATCH/agents/verify/property/{id}?action=changes_required&remarks=...Request changes on propertyGET/agents/dashboardAgent's assigned properties, active deals, pending documents
Properties
MethodEndpointDescriptionGET/properties/allBrowse verified listings (filters: city, purpose, type, price range)GET/properties/mySeller views own listingsGET/properties/{id}Single property detail with ML price estimatePOST/properties/addAdd new property (returns ML price hint)PATCH/properties/{id}Update property (resets verification, extends deadline to 5 days)DELETE/properties/{id}Delete unverified property with no active deal
Interests / Bids
MethodEndpointDescriptionPOST/bid/{property_id}Create interest (returns ML bid warning if >30% off estimate)PATCH/bid/{interest_id}Take action on interestGET/bid/buyerBuyer views their interests with price breakdownGET/bid/sellerSeller views interests on their properties
Interest Actions

Buyer: withdraw, accept_counter, reject_counter
Seller: accept_bid, counter, reject

Deals
MethodEndpointDescriptionGET/deals/myView own dealsPATCH/deals/{deal_id}/payBuyer confirms payment (moves to payment_pending)PATCH/deals/{deal_id}/completeAgent marks deal as completed
Documents
MethodEndpointDescriptionPOST/deals/{deal_id}/documentsUpload document file (multipart, stored on Cloudinary)PATCH/deals/{deal_id}/documents/{doc_id}/verify?status=verifiedAgent verifies documentPATCH/deals/{deal_id}/documents/{doc_id}/verify?status=rejected&notes=...Agent rejects documentGET/deals/{deal_id}/documentsView all documents for a deal
Allowed upload formats: PDF, JPEG, PNG, WEBP — max 10 MB.
ML
MethodEndpointDescriptionGET/ml/price-estimateStandalone price prediction by city, type, area, furnishing, etc.

🗄️ Database Models
User
id, email, password, phone, role, created_at

role is always "customer" on registration — cannot be set by user
Agents have role="agent" set internally

Location
id, city, state, pincode
Property
id, description, location_id, price, property_type, purpose, bedrooms, bathrooms, area, is_available, is_verified, verification_status, remarks, verification_deadline, is_modified, seller_id, agent_id, created_at

verification_status: pending | verified | changes_required
verification_deadline: now + 10 days on creation, now + 5 days on modification
is_modified: set True when seller edits after submission — visible to agent

Agent
id, user_id, name, city, fee_percent, min_fee, max_fee, created_at
Interest
id, property_id, buyer_id, bid_amount, counter_amount, message, agent_id, status, created_at

Unique constraint on (buyer_id, property_id)
Status flow: pending → countered → accepted | agreed | rejected | withdrawn

Deal
id, interest_id, buyer_id, seller_id, property_id, agent_id, seller_price, agent_fee, final_price, status, created_at

Status flow: created → documents_pending → documents_verified → payment_pending → completed | cancelled

DealDocument
id, deal_id, document_type, status, uploaded_by, file_url, cloudinary_public_id, verified_by, notes, reupload_deadline, created_at

Status: pending | verified | rejected
reupload_deadline: now + 7 days on rejection


🔐 Security

JWT-based authentication on all protected routes
role="customer" hardcoded on registration — users cannot self-assign roles
Agents can only be created by existing agents
require_agent dependency guards all agent-only endpoints
Seller cannot bid on their own property
Buyer cannot create duplicate interests on the same property
Only the assigned agent for a property can verify it
Only the assigned agent for a deal can verify its documents or complete the deal
Only the buyer/seller of a deal can upload documents
Cannot upload a new document if one of the same type is already pending or verified


⏰ Automated Scheduler (APScheduler)
Runs three background jobs every 24 hours:
1. Delete expired properties
Finds all unverified properties past their verification_deadline and deletes them.
2. Cancel deals with expired document deadlines
Finds all rejected documents past their reupload_deadline and marks the corresponding deal as cancelled.
3. Retrain ML models
Merges live verified property data from the DB with the base training dataset and retrains both buy/rent models, then reloads them into memory.

💰 Pricing Logic
agent_fee = price × fee_percent / 100
agent_fee = max(min_fee, min(agent_fee, max_fee))

buyer_pays  = negotiated_price + agent_fee
seller_gets = negotiated_price − agent_fee

🤖 Agent Assignment
When a buyer creates an interest, an agent is assigned based on the property's city:

Finds all agents covering that city
Assigns the one with the fewest active deals (load balancing)
Falls back to the default agent if no city match is found
The same agent follows the interest through to the deal and document verification


🧠 ML Price Estimation
Two separate models are trained — one for buy, one for rent — using property features:

City, property type, bedrooms, bathrooms, area (sq ft), furnishing status

ML output appears in three places:

POST /properties/add — returns an ml_price_hint so sellers can calibrate their listing price
GET /properties/{id} — returns ml_estimate, ml_price_range, ml_confidence alongside listing details
POST /bid/{property_id} — returns an ml_warning if the buyer's bid is more than 30% away from the estimated fair price
GET /ml/price-estimate — standalone endpoint for any price query without creating a listing

Models are stored as .joblib files under backend/models_store/ and retrained daily by the scheduler.

👩‍💻 Author
Priyamvada Singh
Backend Developer | Engineering Student
GitHub: https://gith

