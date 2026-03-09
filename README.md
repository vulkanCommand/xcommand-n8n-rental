# xCommand Cloud

xCommand Cloud is a platform that allows users to instantly launch a temporary **n8n automation workspace** in the browser.

Instead of installing n8n locally or configuring servers, users can start a fully isolated workspace in seconds and begin building automation workflows immediately.

Each workspace runs in its own container and automatically expires after the selected duration.

The goal of xCommand Cloud is to make experimentation with automation simple and accessible without requiring infrastructure setup.

---

# What You Can Do

With xCommand Cloud you can:

* launch a dedicated **n8n automation environment**
* build and test automation workflows
* experiment with integrations and APIs
* run temporary automation setups without installation
* access everything directly from your browser

Each workspace is isolated and automatically cleaned up after it expires.

---

# Key Features

### Instant Workspace Launch

A new automation workspace can be started in seconds with no setup required.

### Fully Isolated Environments

Every user workspace runs in its own container to ensure isolation and stability.

### Temporary Workspaces

Workspaces are designed to be short-lived environments for experimentation and testing.

Once the workspace expires, it is automatically removed.

### Free Sandbox

New users can try the platform with a **24-hour free workspace**.

### Capacity Protection

To maintain system performance, the free plan has a limited number of active workspaces.

Example:

```
24 / 25 free workspaces
```

When the limit is reached, new free workspaces are temporarily paused until capacity becomes available.

### Automatic Cleanup

Expired workspaces are automatically stopped and removed by the platform.

### Secure Access

Each workspace is accessed through its own dedicated URL.

Example:

```
https://u-3f81a2.xcommand.cloud
```

### Built-in Monitoring

The platform continuously monitors system health, container usage, and server performance.

---

# How It Works

1. A user selects a plan.
2. The platform provisions a new workspace.
3. A container running n8n is started.
4. A unique workspace URL is generated.
5. The user accesses the workspace through the browser.
6. When the workspace expires, it is automatically removed.

This process typically takes only a few seconds.

---

# Plans

| Plan | Duration |
| ---- | -------- |
| Free | 24 hours |
| $1   | 24 hours |
| $3   | 5 days   |

Paid plans are processed securely through Stripe.

---

# Platform Architecture

xCommand Cloud runs on a container-based infrastructure designed to create and manage automation environments dynamically.

Each workspace is launched inside its own container and routed through a reverse proxy to its dedicated subdomain.

The system includes services for:

* workspace provisioning
* payment processing
* container lifecycle management
* automatic cleanup
* infrastructure monitoring

---

# Monitoring and Reliability

The platform monitors:

* active workspaces
* container performance
* server resource usage
* system health

This ensures that new workspaces can be created without affecting existing users.

---

# Security and Isolation

Every workspace is isolated from other users.

Each environment runs:

* inside its own container
* with its own storage volume
* behind controlled routing

When a workspace expires, all associated resources are removed automatically.

---

# Author

Durga Kalyan Gandiboyina

AI Engineer • Full-Stack Developer • Automation Builder

---

# Vision

The long-term goal of xCommand Cloud is to make automation environments instantly accessible.

Instead of installing tools, configuring servers, or managing infrastructure, users should be able to start building automation workflows immediately from the browser.
