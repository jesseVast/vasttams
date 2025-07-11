# Security Guide for TAMS API

This document provides security best practices and setup instructions for deploying the TAMS API securely, including:
- Adding an NGINX front-end for TLS termination
- Generating self-signed certificates
- Kubernetes (K8s) deployment with NGINX for TLS
- Summary of authentication and authorization

---

## 1. NGINX Front-End for TLS Termination

**Why NGINX?**
- Acts as a reverse proxy
- Handles HTTPS (TLS) termination
- Can enforce security headers and rate limiting

### Example NGINX Configuration

```
server {
    listen 443 ssl;
    server_name your.domain.com;

    ssl_certificate     /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;

    location / {
        proxy_pass http://app:8000;  # FastAPI app
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- Place your certificates in `/etc/nginx/certs/`.
- Update `proxy_pass` to match your FastAPI backend.

### Running NGINX with Docker

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./cert.pem:/etc/nginx/certs/cert.pem:ro
      - ./key.pem:/etc/nginx/certs/key.pem:ro
    depends_on:
      - app
  app:
    build: .
    expose:
      - "8000"
```

---

## 2. Generating Self-Signed Certificates

See `generate_self_signed_cert.sh` for a script to generate certificates for development/testing.

---

## 3. Kubernetes (K8s) with NGINX Ingress for TLS

- Use [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- Store TLS certs as Kubernetes secrets

### Example Steps

1. **Create TLS Secret:**
   ```sh
   kubectl create secret tls tams-tls --cert=cert.pem --key=key.pem
   ```
2. **Ingress YAML:**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: tams-ingress
     annotations:
       nginx.ingress.kubernetes.io/ssl-redirect: "true"
   spec:
     tls:
     - hosts:
       - your.domain.com
       secretName: tams-tls
     rules:
     - host: your.domain.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: tams-api
               port:
                 number: 8000
   ```

---

## 4. Authentication & Authorization Summary

- Use OAuth2/JWT for authentication (see main README for details)
- Restrict sensitive endpoints with role-based authorization
- Always use HTTPS in production
- Rotate secrets and certificates regularly

---

**For more details, see the main README and code comments.** 