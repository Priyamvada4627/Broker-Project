# Broker Project - Progress Log

## Project Overview
A FastAPI + PostgreSQL property brokerage backend. Two cycles:
- **Interest Cycle**: Seller posts property → Buyer creates interest → Negotiate via state changes → Deal created
- **Deal Cycle**: Document verification by agent → Payment → Completion

Two roles: `customer` (buyers/sellers) and `agent`

---

## Tech Stack
- FastAPI
- PostgreSQL
- SQLAlchemy (ORM)
- Alembic (migrations)
- Pydantic V2
- JWT Auth (python-jose)
- Uvicorn

---

## Project Structure
```
backend/
├── routers/
│   ├── auth.py        # login
│   ├── bid.py         # interest/negotiation endpoints
│   ├── property.py    # property CRUD
│   ├── user.py        # user registration, /me
│   ├── agent.py       # agent registration, property verification
│   ├── deal.py        # GET /deals/my
│   └── document.py    # deal document upload + verification
├── services/
│   ├── agent.py       # get_platform_agent with load balancing
│   ├── deal.py        # create_deal_from_interest
│   └── pricing.py     # fee computation, effective price
├── schemas/
│   ├── user.py
│   ├── property.py
│   ├── bid.py
│   └── deal.py
├── models.py
├── database.py
├── oauth2.py
├── utils.py
├── config.py
└── main.py
alembic/
requirements.txt
```

---

## Models

### User
```python
id, email, password, phone, role (default="customer"), created_at
```

### Location (NEW)
```python
id, city, state, pincode
```

### Property
```python
id, description, location_id (FK→locations), price, property_type (enum), 
purpose (enum), is_available, is_verified, verified_by (FK→agents), 
seller_id (FK→users), created_at
relationships: location (→Location), interests (→Interest)
```

### Agent
```python
id, user_id (FK→users, unique), name, city, fee_percent, min_fee, max_fee, created_at
```

### Interest
```python
id, property_id (FK→properties), buyer_id (FK→users), bid_amount, 
counter_amount, message, agent_id (FK→agents), status, created_at
unique constraint: (buyer_id, property_id)
status values: pending | countered | accepted | agreed | rejected | withdrawn
```

### Deal
```python
id, interest_id (FK→interests, unique), buyer_id, seller_id, 
property_id (FK→properties, unique), agent_id (FK→agents),
seller_price, agent_fee, final_price, status (default="created"), created_at
status values: created → documents_pending → documents_verified → payment_pending → completed
```

### DealDocument (NEW)
```python
id, deal_id (FK→deals), document_type, status (default="pending"),
uploaded_by (FK→users), file_url, verified_by (FK→agents), notes, created_at
status values: pending | verified | rejected
document_type examples: title_deed | NOC | encumbrance | identity_proof | sale_agreement
```

---

## Enums

### PropertyPurpose
```python
buy | sell | rent
```

### PropertyType
```python
apartment | house | flat | plot | commercial
```

---

## API Endpoints

### Auth
- `POST /login` — returns JWT token

### Users
- `POST /users/register` — creates customer (role hardcoded to "customer")
- `GET /users/me` — returns current user profile

### Agents
- `POST /agents/register` — creates new agent (only callable by existing agent)
- `PATCH /agents/verify/property/{property_id}` — agent verifies a property listing

### Properties
- `GET /properties/all` — browse all properties with filters (city, purpose, type, price range)
- `GET /properties/my` — seller sees their own properties with interests
- `GET /properties/{id}` — single property detail
- `POST /properties/add` — seller adds a property (creates Location first, then Property)

### Bids/Interests
- `POST /bid/{property_id}` — buyer creates interest
- `PATCH /bid/{interest_id}` — buyer or seller takes action on interest
- `GET /bid/buyer` — buyer sees all their interests
- `GET /bid/seller` — seller sees all interests on their properties

#### Interest Actions
- Buyer: `withdraw`, `accept_counter`, `reject_counter`
- Seller: `accept_bid`, `counter`, `reject`

#### Deal Auto-Creation
When interest status becomes `accepted` or `agreed`:
- Deal is created automatically
- Property marked unavailable
- All other interests on that property rejected

### Deals
- `GET /deals/my` — buyer or seller sees their deals

### Documents
- `POST /deals/{deal_id}/documents` — buyer/seller uploads a document (file_url as string)
- `PATCH /deals/{deal_id}/documents/{document_id}/verify` — agent verifies/rejects a document
- `GET /deals/{deal_id}/documents` — buyer, seller, or agent views all documents for a deal

When all documents are verified → deal status auto-updates to `documents_verified`

---

## Key Services

### services/agent.py — get_platform_agent
- Takes optional `city` parameter
- Finds agent in that city with fewest active deals (load balancing)
- Falls back to agent named "default" if no city match

### services/pricing.py
- `get_accepted_amount(interest)` — returns negotiated price based on status
- `compute_money_view(base_amount, agent)` — returns buyer_pays, seller_gets, agent_fee
- `get_effective_price(property_price, interest)` — returns current effective price
- `compute_agent_fee(price, agent)` — respects min_fee and max_fee bounds

### services/deal.py — create_deal_from_interest
- Guards against duplicate deals
- Computes pricing via pricing service
- Creates Deal record

---

## Security

### oauth2.py
- `create_access_token(data)` — creates JWT
- `verify_access_token(token, exception)` — validates JWT
- `get_current_user(token, db)` — returns User object
- `require_agent(current_user)` — NEW: raises 403 if user role != "agent"

---

## Business Rules Implemented
1. Users cannot self-assign role — always defaults to "customer"
2. Agents created only by existing agents via `/agents/register`
3. Seller cannot bid on their own property
4. Buyer cannot create duplicate interests on same property
5. Deal created automatically when interest is accepted/agreed
6. All other interests rejected when deal is created
7. Property marked unavailable when deal is created
8. Agent assigned by property city — least loaded agent wins
9. Document verification gates deal progression
10. Only deal's assigned agent can verify its documents
11. Only buyer/seller of a deal can upload documents

---

## Remaining Work

### High Priority
- **Rent-specific logic** — rent has different deal structure:
  - Monthly amount instead of one-time price
  - Deposit amount
  - Duration (start date, end date)
  - Deal cycle differs from sale
- **Agent dashboard** — agent needs endpoints to see:
  - All properties assigned to them
  - All deals assigned to them
  - All pending documents awaiting verification
- **Update/delete property** — seller cannot currently edit or remove their listing

### Medium Priority
- **Payment stage** — after documents_verified, deal should move to payment_pending
  - Payment confirmation endpoint
  - Deal moves to "completed"
- **Filter by location** — `GET /properties/all` city filter should now use `location.city` 
  via join instead of old string field
- **BuyerPropertyOut schema** — should include location details (city, state, pincode)
  instead of nothing after removing old location string

### Low Priority / Future
- AWS S3 or Cloudinary for actual file uploads (currently using URL strings)
- ML price prediction for properties
- Redis caching
- Docker setup
- Unit and integration tests
- Multi-agent area coverage (currently one agent per city)

---

## Known Issues / Watch Points
- `location` field was removed from Property and replaced with `location_id` FK
  — make sure all endpoints that referenced `property.location` string are updated
  to use `property.location.city` via relationship
- Agent `city` field should match property location cities for assignment to work
- Default agent (name="default") must always exist in DB as fallback
- First agent was manually inserted into DB with SQL, password is placeholder
  — should be updated via seed script

---

## Database Notes
- Default agent seeded manually via SQL
- Agent user has role="agent", all other users have role="customer"
- Alembic manages all schema changes — never edit DB directly for schema

---

## How to Run
```bash
# activate venv
venv\Scripts\activate

# run server
uvicorn backend.main:app --reload

# create migration
alembic revision --autogenerate -m "description"

# apply migration
alembic upgrade head
```

API docs available at: http://127.0.0.1:8000/docs