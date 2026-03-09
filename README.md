# xCommand Cloud

xCommand Cloud is a small platform that lets users launch a temporary **n8n automation workspace** instantly in the browser. Instead of installing n8n locally or configuring infrastructure, users can start a dedicated environment in seconds and begin building workflows right away.

Each workspace runs inside its own Docker container and is automatically removed after it expires. The goal is to make it easy to test automation ideas without worrying about setup or server management.

---

# What This Project Does

xCommand Cloud provides temporary environments for experimenting with automation using **n8n**.

Instead of installing n8n locally, users can launch a workspace from the website and immediately access the full n8n UI through their browser.

Each workspace is:

* isolated from other users
* created on demand
* accessible through a unique subdomain
* automatically cleaned up after expiration

This makes it useful for:

* testing automation ideas
* learning n8n
* quick workflow experiments
* demos or workshops

---

# Core Features

### Instant Workspace Launch

A new n8n workspace can be created in seconds.

### Container Isolation

Every workspace runs inside its own Docker container with its own storage volume.

### Temporary Workspaces

Workspaces automatically expire and are removed by a background cleanup service.

### Free Sandbox

Users can try the platform with a **24-hour free workspace**.

### Workspace Capacity Control

To keep the server stable, the free plan has a limited number of active workspaces.

Example:

```
24 / 25 free workspaces
```

When the limit is reached, new free workspaces are temporarily blocked until one expires.

### Automatic Cleanup

A janitor service periodically removes expired containers and volumes.

### Stripe Payments

Paid plans are handled using Stripe Checkout.

### AI Support Endpoint

The API includes a small support assistant that can answer questions about the platform.

### System Monitoring

Infrastructure metrics are collected using:

* Prometheus
* Grafana
* cAdvisor
* Node Exporter

---

# System Architecture

The platform uses a small container-based architecture.

```
Internet
   │
   ▼
Traefik (reverse proxy)
   │
   ├── Landing Page
   ├── API Service
   └── n8n Workspaces
```

### Main Services

| Service            | Purpose                                                   |
| ------------------ | --------------------------------------------------------- |
| **API (FastAPI)**  | Handles provisioning, plan limits, and Stripe integration |
| **Web**            | Landing page and frontend                                 |
| **Worker**         | Background processing tasks                               |
| **Janitor**        | Removes expired workspaces                                |
| **PostgreSQL**     | Stores workspace metadata                                 |
| **Traefik**        | Routes subdomains to containers                           |
| **n8n Containers** | Individual automation environments                        |

---

# Workspace Lifecycle

1. A user selects a plan.
2. The API provisions a new workspace.
3. Docker starts an n8n container.
4. A workspace URL is generated.

Example:

```
https://u-3f81a2.xcommand.cloud
```

5. The user works inside the workspace.
6. After expiration, the janitor service stops and deletes the container.

---

# Free Plan Logic

The free plan provides a temporary **24-hour workspace**.

To prevent server overload, the platform limits how many free workspaces can run at the same time.

```
FREE_WORKSPACE_LIMIT = 25
```

The frontend checks the API to display the current capacity:

```
GET /plans/free/status
```

Example response:

```json
{
  "ok": true,
  "plan": "free",
  "limit": 25,
  "active_count": 12,
  "remaining": 13,
  "available": true,
  "display": "12/25 free workspaces"
}
```

If the limit is reached, the API prevents new free workspaces from being created.

---

# Paid Plans

| Plan | Duration |
| ---- | -------- |
| $1   | 24 hours |
| $3   | 5 days   |

Payments are processed through **Stripe Checkout**.
Once payment is completed, the API automatically provisions the workspace.

---

# Technology Stack

### Backend

* FastAPI
* Python
* PostgreSQL
* Docker
* Stripe API
* OpenAI API

### Infrastructure

* Docker Compose
* Traefik
* Prometheus
* Grafana
* cAdvisor
* Node Exporter

### Automation Engine

* n8n

### Frontend

* Lovable.dev generated UI
* HTML / CSS / JavaScript

---

# Monitoring

The system exposes internal metrics such as:

* active workspaces
* container usage
* CPU usage
* memory usage

These metrics are visualized through Grafana dashboards.

Example endpoint:

```
/metrics/active-workspaces
```

---

# Security and Isolation

Each workspace runs:

* inside its own container
* with its own storage volume
* isolated from other users

Expired containers and volumes are removed automatically to prevent resource abuse.

---

# Project Structure

```
xcommand-n8n-rental
│
├── api/                # FastAPI backend
├── web/                # landing UI
├── worker/             # background job worker
├── janitor/            # workspace cleanup service
├── infra/              # Docker compose and infrastructure config
├── monitoring/         # Prometheus and Grafana configs
└── scripts/            # deployment scripts
```

---

# Running Locally

Clone the repository:

```
git clone https://github.com/<your-username>/xcommand-n8n-rental
```

Start the stack:

```
docker compose up -d
```

This starts the API, database, monitoring tools, and supporting services locally.

---

# Deployment

The production environment runs on a VPS using Docker Compose and Traefik.

Each workspace is assigned its own subdomain dynamically, for example:

```
u-4f91c1.xcommand.cloud
```

Traefik automatically routes traffic to the correct container.

---

# Why This Project Matters

This project shows how to build a real SaaS platform that can:

* create containerized environments on demand
* isolate users securely
* manage container lifecycles automatically
* integrate payments
* enforce platform capacity limits
* monitor infrastructure in production

It combines backend development, infrastructure management, and SaaS design into a single system.

---

# Author

Durga Kalyan Gandiboyina
AI Engineer · Full-Stack Developer · Automation Builder

---

# Future Improvements

Some ideas for the next iteration:

* multi-region deployment
* container autoscaling
* user dashboards
* longer-lived paid workspaces
* team collaboration support
