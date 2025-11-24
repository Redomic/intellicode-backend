# IntelliCode Backend

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![ArangoDB](https://img.shields.io/badge/ArangoDB-D7E317?style=for-the-badge&logo=arangodb&logoColor=333)
![LangGraph](https://img.shields.io/badge/LangGraph-F0F0F0?style=for-the-badge)

**IntelliCode (IntelliT)** is an adaptive learning platform that bridges Intelligent Tutoring Systems (ITS) with coordinated Large Language Model (LLM) agents. This backend serves as the centralized "StateGraph Orchestrator," managing learner state, agent coordination, and curriculum adaptation.

This implementation is the reference backend for the architecture described in *IntelliCode - Multi-Agent LLM Intelligent Teaching System: A Principled Architecture with Centralized Learner Modeling*.

---

## System Architecture

![System Architecture](architecture.png)

The backend is architected around a **StateGraph Orchestrator** that maintains a single source of truth for the learner's state. It coordinates specialized agents (Pedagogical Feedback, Content Curator, etc.) to provide personalized learning experiences.

## Technical Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **API Framework** | FastAPI | High-performance, easy-to-learn, fast-to-code, ready-for-production |
| **Orchestration** | LangGraph | Library for building stateful, multi-actor applications with LLMs |
| **Database** | ArangoDB | Multi-model graph database for flexible learner state modeling |
| **LLM Provider** | Gemini / Bedrock | Configurable LLM backend for agent intelligence |

## Getting Started

### Prerequisites

*   **Python**: Version 3.10+
*   **Conda**: Recommended for environment management
*   **Docker**: For running the local database instance

### 1. Database Setup

We use Docker Compose to spin up a local ArangoDB instance with the required configuration.

```bash
# Navigate to backend directory
cd backend

# Start ArangoDB
docker-compose up -d
```

This will start ArangoDB on `http://localhost:8529` with the default credentials configured in the application (`root` / `openSesame`).

### 2. Environment Setup

Create and activate the Conda environment:

```bash
# Create environment from config
conda env create -f environment.yml

# Activate the environment
conda activate intellicode
```

### 3. Database Seeding

Before running the application, you need to seed the database with questions and roadmap data. We provide scripts to automate this.

**A. Scrape and Prepare Data**

```bash
cd scripts

# Scrape roadmap data (generates production_roadmap.json)
python standalone_roadmap_scraper.py --output production_roadmap.json
```

**B. Import Data**

```bash
# Import data into ArangoDB (filters paid questions by default)
python import_roadmap_data.py production_roadmap.json --force
```

**C. Verify Database Collections**

Run the collection check utility to ensure everything is set up correctly:

```bash
cd .. # back to backend root
python ensure_collections.py
```

### 4. Running the Server

Start the FastAPI development server:

```bash
# Ensure you are in the backend root and environment is activated
conda activate intellicode

# Run the server
python run.py
```

The API will be available at `http://localhost:8000`.
*   **API Docs**: `http://localhost:8000/docs`
*   **ReDoc**: `http://localhost:8000/redoc`

## Project Structure

*   `app/agents`: Specialized LLM agent implementations (Feedback, Profiler, etc.).
*   `app/core`: Configuration and security settings.
*   `app/db`: Database connection and abstraction layers.
*   `app/api`: API route handlers.
*   `scripts/`: Utilities for data scraping, seeding, and maintenance.
