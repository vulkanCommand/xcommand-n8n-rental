# xCommand Cloud

**xCommand Cloud** is a lightweight SaaS platform that lets users instantly launch **isolated n8n automation workspaces** in seconds — without installing anything or managing servers.

Users can spin up a temporary n8n instance, experiment with automation workflows, and access the full n8n UI through a secure browser workspace.

The platform provisions containerized environments on demand and automatically cleans them up after expiration.

---

# 🚀 What This Project Does

xCommand Cloud provides **ephemeral automation environments** for developers and builders who want to quickly experiment with n8n workflows.

Instead of installing n8n locally, users can launch a dedicated environment in seconds.

Each workspace is:

* isolated
* containerized
* automatically expired
* instantly accessible via browser

This makes it perfect for:

* testing automation ideas
* learning n8n
* temporary workflow experiments
* demos or workshops

---

# ⚡ Core Features

### Instant Workspace Launch

Users can spin up a dedicated n8n container with a single click.

### Isolated Environments

Every workspace runs in its own Docker container with a dedicated volume.

### Temporary Access

Workspaces automatically expire and are cleaned up by the system.

### Free Sandbox Plan

Users can try the platform instantly with a **24-hour free workspace**.

### Workspace Capacity Control

The platform limits free plan capacity to prevent server overload.

Example:

```
24 / 25 free workspaces
```

If capacity is reached, users are asked to return later.

### Automatic Cleanup

A background janitor service removes expired containers and volumes.

### Payment Integration

Paid plans are handled through **Stripe Checkout**.

### Built-in Support Assistant

An AI support endpoint helps users with questions related to the platform.

### Monitoring & Metrics

System metrics are collected using:

* Prometheus
* Grafana
* cAdvisor
* Node Exporter

---

# 🏗️ System Architecture

The platform is built using a micro-service style architecture.

```
Internet
   │
   ▼
Traefik (reverse proxy)
   │
   ├── Landing Page
   ├── API Service
   └── Dynamic n8n Workspaces
```

### Services

| Service            | Description                                                    |
| ------------------ | -------------------------------------------------------------- |
| **API (FastAPI)**  | Handles provisioning, workspace limits, and Stripe integration |
| **Web**            | Landing page and UI                                            |
| **Worker**         | Background job processing                                      |
| **Janitor**        | Removes expired workspaces                                     |
| **PostgreSQL**     | Stores workspace metadata                                      |
| **Traefik**        | Routes subdomains to workspace containers                      |
| **n8n Containers** | Per-user automation environments                               |

---

# 🧠 Workspace Lifecycle

1️⃣ User selects a plan
2️⃣ API provisions a new workspace
3️⃣ Docker container starts an n8n instance
4️⃣ Workspace URL is generated

Example:

```
https://u-3f81a2.xcommand.cloud
```

5️⃣ User works inside the environment
6️⃣ After expiration the janitor service stops and deletes the container

---

# 🆓 Free Plan Logic

The free plan provides a **24-hour sandbox workspace**.

To prevent server overload the platform enforces a capacity limit.

```
FREE_WORKSPACE_LIMIT = 25
```

The API tracks active free workspaces using:

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

If the limit is reached, the API blocks new workspace creation.

---

# 💳 Paid Plans

| Plan | Duration |
| ---- | -------- |
| $1   | 24 hours |
| $3   | 5 days   |

Payments are handled via **Stripe Checkout**.

After successful payment the API provisions the workspace automatically.

---

# 🧩 Technology Stack

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

### Automation Runtime

* n8n

### Frontend

* Lovable.dev generated UI
* HTML / CSS / JS

---

# 📊 Monitoring

The platform exposes internal metrics such as:

* active workspaces
* container usage
* CPU utilization
* memory usage

These metrics are visualized through Grafana dashboards.

Example metrics endpoint:

```
/metrics/active-workspaces
```

---

# 🔐 Security & Isolation

Each workspace runs:

* inside its own container
* with its own Docker volume
* isolated from other users

Containers are removed after expiration to prevent resource abuse.

---

# 📁 Project Structure

```
xcommand-n8n-rental
│
├── api/                # FastAPI backend
├── web/                # landing UI
├── worker/             # background job worker
├── janitor/            # workspace cleanup service
├── infra/              # docker compose + infra configs
├── monitoring/         # prometheus / grafana configs
└── scripts/            # deployment scripts
```

---

# 🧪 Local Development

Clone the repository:

```
git clone https://github.com/<your-username>/xcommand-n8n-rental
```

Start the stack:

```
docker compose up -d
```

Services will be available locally.

---

# 🌐 Production Deployment

The platform runs on a VPS with:

* Docker Compose
* Traefik for routing
* automatic container provisioning

Each workspace is assigned a subdomain dynamically.

Example:

```
u-4f91c1.xcommand.cloud
```

---

# 🎯 Why This Project Is Interesting

This project demonstrates how to build a **real SaaS platform** that:

* provisions infrastructure dynamically
* isolates user environments
* manages container lifecycles
* integrates payments
* enforces resource limits
* monitors infrastructure health

It combines **backend engineering, DevOps, and cloud architecture** into one system.

---

# 👨‍💻 Author

**Durga Kalyan Gandiboyina**

AI Engineer • Full-Stack Developer • Automation Builder

---

# ⭐ Future Improvements

* multi-region workspace deployment
* autoscaling container pools
* user dashboards
* persistent paid workspaces
* team collaboration support
