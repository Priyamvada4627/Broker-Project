# 🏠 Broker Project

A production-style property brokerage backend built with **FastAPI** and **PostgreSQL**, featuring a complete interest-to-deal lifecycle, agent assignment, document verification, and role-based access control.

---

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Auth | JWT (python-jose) |
| Validation | Pydantic V2 |
| Server | Uvicorn |
| Scheduler | APScheduler |

---

## ⚙️ Setup

### 1. Clone the repository
```bash
git clone https://github.com/Priyamvada4627/Broker-Project.git
cd Broker-Project
```

### 2. Create and activate virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:
```env
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_password
DATABASE_NAME=your_database
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. Apply migrations
```bash
alembic upgrade head
```

### 6. Seed the default agent

Run the seed script to create the default platform agent with a properly hashed password:
```bash
python -m backend.seed
```

This creates:
- User: `agent@platform.com` / password: `securepassword`
- Default agent with `fee_percent=2.0`, `min_fee=1000`, `max_fee=50000`

### 7. Run the server
```bash
uvicorn backend.main:app --reload
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🏗️ Architecture

```
Client
  ↓
Routers (API Layer)       — HTTP handling, request validation
  ↓
Services (Business Logic) — pricing, deal creation, agent assignment
  ↓
Models (ORM Layer)        — SQLAlchemy models
  ↓
PostgreSQL Database
```

---

## 📂 Project Structure

```
backend/
├── routers/
│   ├── auth.py          # Login
│   ├── user.py          # Registration, profile
│   ├── property.py      # Property CRUD + update
│   ├── bid.py           # Interest & negotiation
│   ├── deal.py          # Deal retrieval
│   ├── document.py      # Document upload & verification
│   └── agent.py         # Agent registration & property verification
├── services/
│   ├── agent.py         # Agent assignment with load balancing
│   ├── deal.py          # Deal creation logic
│   └── pricing.py       # Fee computation
├── schemas/
│   ├── user.py
│   ├── property.py
│   ├── bid.py
│   └── deal.py
├── models.py            # All database models
├── database.py          # DB connection
├── oauth2.py            # JWT auth + role guards
├── utils.py             # Password hashing
├── config.py            # Environment config
├── seed.py              # Default agent seeder
└── main.py              # App entrypoint + scheduler
```

---

## 🔄 System Flow

### Property Verification Cycle
```
Seller posts property
        ↓
System sets verification_deadline = now + 10 days
        ↓
Agent reviews property
        ↓
Agent: verified → property is live
Agent: changes_required → seller gets remarks, deadline resets to 5 days
        ↓
If not verified before deadline → auto deleted by scheduler
```

### Interest Cycle
```
Seller posts property
        ↓
Buyer creates interest (bid_amount optional)
        ↓
Seller: accept_bid | counter | reject
        ↓
Buyer: accept_counter | reject_counter | withdraw
        ↓
Deal auto-created when interest is accepted/agreed
All other interests on that property → rejected
Property marked unavailable
```

### Deal Cycle
```
Deal created
        ↓
Buyer & Seller upload documents (file URL)
        ↓
Agent verifies each document → verified | rejected
        ↓
If rejected → seller/buyer gets rejection notes + 7 days to re-upload
If not re-uploaded in 7 days → deal cancelled by scheduler
        ↓
All verified → deal status: documents_verified
        ↓
Payment → completed  (in progress)
```

---

## 📌 API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/login` | Get JWT token |

### Users
| Method | Endpoint | Description |
|---|---|---|
| POST | `/users/register` | Register as customer |
| GET | `/users/me` | Get own profile |

### Agents
| Method | Endpoint | Description |
|---|---|---|
| POST | `/agents/register` | Create new agent (agent only) |
| PATCH | `/agents/verify/property/{id}?action=verified` | Verify a property listing |
| PATCH | `/agents/verify/property/{id}?action=changes_required&remarks=...` | Request changes on property |

### Properties
| Method | Endpoint | Description |
|---|---|---|
| GET | `/properties/all` | Browse all properties (with filters) |
| GET | `/properties/my` | Seller views own listings |
| GET | `/properties/{id}` | Single property detail |
| POST | `/properties/add` | Add new property |
| PATCH | `/properties/{id}` | Update property (resets verification) |

### Interests / Bids
| Method | Endpoint | Description |
|---|---|---|
| POST | `/bid/{property_id}` | Create interest |
| PATCH | `/bid/{interest_id}` | Take action on interest |
| GET | `/bid/buyer` | Buyer views their interests |
| GET | `/bid/seller` | Seller views interests on their properties |

#### Interest Actions
- **Buyer**: `withdraw`, `accept_counter`, `reject_counter`
- **Seller**: `accept_bid`, `counter`, `reject`

### Deals
| Method | Endpoint | Description |
|---|---|---|
| GET | `/deals/my` | View own deals |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| POST | `/deals/{deal_id}/documents?document_type=...&file_url=...` | Upload document |
| PATCH | `/deals/{deal_id}/documents/{doc_id}/verify?status=verified` | Agent verifies document |
| PATCH | `/deals/{deal_id}/documents/{doc_id}/verify?status=rejected&notes=...` | Agent rejects document |
| GET | `/deals/{deal_id}/documents` | View all documents for a deal |

---

## 🗄️ Database Models

### User
`id, email, password, phone, role, created_at`
- `role` is always `"customer"` on registration — cannot be set by user
- Agents have `role="agent"` set internally

### Location
`id, city, state, pincode`

### Property
`id, description, location_id, price, property_type, purpose, is_available, is_verified, verified_by, verification_status, remarks, verification_deadline, is_modified, seller_id, agent_id, created_at`
- `verification_status`: `pending | verified | changes_required`
- `verification_deadline`: set to `now + 10 days` on creation, resets to `now + 5 days` on modification
- `is_modified`: set to `True` when seller edits after submission — visible to agent

### Agent
`id, user_id, name, city, fee_percent, min_fee, max_fee, created_at`

### Interest
`id, property_id, buyer_id, bid_amount, counter_amount, message, agent_id, status, created_at`
- Unique constraint on `(buyer_id, property_id)`
- Status: `pending → countered → accepted/agreed/rejected/withdrawn`

### Deal
`id, interest_id, buyer_id, seller_id, property_id, agent_id, seller_price, agent_fee, final_price, status, created_at`
- Status: `created → documents_pending → documents_verified → payment_pending → completed | cancelled`

### DealDocument
`id, deal_id, document_type, status, uploaded_by, file_url, verified_by, notes, reupload_deadline, created_at`
- Status: `pending | verified | rejected`
- `reupload_deadline`: set to `now + 7 days` on rejection

---

## 🔐 Security

- JWT-based authentication on all protected routes
- `role="customer"` hardcoded on registration — users cannot self-assign roles
- Agents can only be created by existing agents
- `require_agent` dependency guards all agent-only endpoints
- Seller cannot bid on their own property
- Buyer cannot create duplicate interests on the same property
- Only the assigned agent for a property can verify it
- Only a deal's assigned agent can verify its documents
- Only the buyer/seller of a deal can upload documents
- Cannot upload a new document if one of the same type is already pending/verified

---

## ⏰ Automated Scheduler (APScheduler)

Runs two background jobs every 24 hours:

**1. Delete expired properties:**
- Finds all unverified properties past their `verification_deadline`
- Deletes them automatically

**2. Cancel deals with expired document deadlines:**
- Finds all rejected documents past their `reupload_deadline`
- Marks the corresponding deal as `cancelled`

---

## 💰 Pricing Logic

Agent fee is computed as a percentage of the negotiated price, bounded by `min_fee` and `max_fee`:

```
agent_fee = price × fee_percent / 100
agent_fee = max(min_fee, min(agent_fee, max_fee))

buyer_pays  = negotiated_price + agent_fee
seller_gets = negotiated_price - agent_fee
```

---

## 🤖 Agent Assignment

When an interest is created, an agent is assigned based on the property's city:
- Finds all agents covering that city
- Assigns the one with the **fewest active deals** (load balancing)
- Falls back to the default agent if no city match found
- The same agent follows the interest through to the deal

---

## 🗺️ Roadmap

- [x] Property verification with remarks and deadline
- [x] Auto-deletion of expired unverified properties
- [x] Update property (resets verification + extends deadline)
- [x] Document rejection with re-upload deadline
- [x] Auto-cancellation of deals with expired document deadlines
- [x] Agent dashboard (assigned properties, deals, pending documents)
- [x] Payment stage and deal completion
- [x] File storage via AWS S3 or Cloudinary
- [x] ML-based property price prediction
- [x] Unit and integration tests

---

## 👩‍💻 Author

**Priyamvada Singh**
Backend Developer | Engineering Student
GitHub: [https://github.com/Priyamvada4627](https://github.com/Priyamvada4627)


