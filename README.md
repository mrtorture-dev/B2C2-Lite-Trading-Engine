# B2C2-Lite Trading Engine 🚀

A high-performance, transactional trading engine backend simulating a cryptocurrency exchange ledger. Designed to demonstrate proficiency in **Python, Django, Async Architectures, and ACID compliance**.

## 📋 Features

* **Transactional Integrity (ACID):** Uses PostgreSQL atomic transactions and `select_for_update` row locking to prevent race conditions and double-spending.
* **Real-time Data:** Background workers (Celery + Redis) fetch live BTC prices from external APIs asynchronously.
* **Automated Scheduling:** Celery Beat updates market data every 30 seconds automatically.
* **REST API:** Fully documented endpoints for portfolio management and order execution via Django Rest Framework (DRF).
* **Containerized:** "Plug and play" environment using Docker and Docker Compose.
* **TDD Approach:** Core logic protected by Pytest suites covering edge cases (e.g., insufficient funds, negative balances).

## 🧠 Why Python instead of C++?

While C++ is the industry standard for ultra-low latency High-Frequency Trading (HFT) engines due to its deterministic memory management and raw execution speed, this specific engine was built in **Python** for the following strategic reasons:

1. **Development Velocity & Prototyping:** Python's rich ecosystem (Django, Celery) allows for rapid prototyping of complex architectural patterns (message queues, async workers) in days rather than weeks.
2. **I/O Bound Architecture:** This engine acts as a "Lite" backend dealing heavily with network requests (fetching external prices) and database transactions. The bottleneck here is I/O, not CPU. Python's `asyncio` and Celery workers handle I/O bound tasks exceptionally well.
3. **Database Concurrency:** The core challenge solved here is ACID compliance and row-level locking (`select_for_update`) within the PostgreSQL ledger. The database layer handles the transactional integrity, making the application language speed less critical for this specific boundary.
4. **C-Extensions:** Critical numerical operations in Python can easily be offloaded to C-based libraries (NumPy, Pandas) if CPU bottlenecks arise in pricing models.

## 🛠 Tech Stack

* **Language:** Python 3.10
* **Framework:** Django 4.2 + DRF
* **Database:** PostgreSQL 15
* **Async/Queue:** Redis + Celery
* **Testing:** Pytest
* **Infrastructure:** Docker & Docker Compose

## 🚀 How to Run

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/TU_USUARIO/b2c2-trading-engine.git](https://github.com/TU_USUARIO/b2c2-trading-engine.git)
    cd b2c2-trading-engine
    ```

2.  **Create a `.env` file:**
    Copy the example configuration:
    ```bash
    # Linux/Mac
    cp .env.example .env 
    # Or just create a .env file with DB_NAME=b2c2_db, DB_USER=b2c2_user, DB_PASSWORD=b2c2_password, DB_HOST=db
    ```

3.  **Start the Engine:**
    ```bash
    docker-compose up --build
    ```
    *The system will spin up Django, Postgres, Redis, a Celery Worker, and the Beat scheduler.*

4.  **Access:**
    * API Root: `http://localhost:8000/api/`
    * Admin Panel: `http://localhost:8000/admin/`

## 🧪 Running Tests

To verify the financial logic and transactional safety:

```bash
docker-compose exec web pytest
