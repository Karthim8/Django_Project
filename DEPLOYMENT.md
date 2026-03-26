# 🚀 AWS EC2 Deployment Guide: Hosting NexusLink

This guide provides a comprehensive, step-by-step walkthrough for hosting the NexusLink project on **AWS EC2** (Ubuntu Linux).

---

## 🏗️ Step 1: AWS Console Configuration

### 1. Launch instance
- **OS**: Ubuntu 22.04 LTS
- **Instance Type**: `t2.medium` (Recommended) or `t3.medium`. Avoid `t2.micro` as AI tasks/Celery might crash it.
- **Key Pair**: Create new and download your `.pem` file.

### 2. Configure Security Groups
In the AWS Console under **Security Groups**, add these **Inbound Rules**:
| Protocol | Port | Source | Description |
| :--- | :--- | :--- | :--- |
| SSH | 22 | My IP | Your access |
| HTTP | 80 | 0.0.0.0/0 | Web traffic |
| HTTPS | 443 | 0.0.0.0/0 | Secure web traffic |
| Custom TCP | 8001 | 0.0.0.0/0 | Daphne (WebSockets) |

### 3. Elastic IP (Highly Recommended)
1. Go to **Elastic IPs** in the EC2 Dashboard.
2. Select **Allocate Elastic IP address**.
3. **Associate** it with your running instance.
*This ensures your website's IP never changes even if you restart the server.*

---

## 🛠️ Step 2: Connect and Install Setup
1. **Login via SSH**:
   ```bash
   chmod 400 your-key.pem
   ssh -i your-key.pem ubuntu@your-elastic-ip
   ```
2. **Setup System**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3-pip python3-venv nginx git libpq-dev postgresql postgresql-contrib
   ```

---

## 🗄️ Step 3: Database & Project Setup
1. **PostgreSQL Setup**:
   ```bash
   sudo -u postgres psql
   # inside psql:
   CREATE DATABASE nexuslink;
   CREATE USER nexususer WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE nexuslink TO nexususer;
   \q
   ```
2. **Project Clone & Environment**:
   ```bash
   git clone https://github.com/your-username/your-repo.git /var/www/nexuslink
   cd /var/www/nexuslink
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn daphne uvicorn
   nano .env # Add your production secrets here
   ```

---

## ⚙️ Step 4: System Services (Systemd)

### 1. Gunicorn (HTTP)
`sudo nano /etc/systemd/system/gunicorn.service`
```ini
[Unit]
Description=Gunicorn daemon
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/nexuslink
ExecStart=/var/www/nexuslink/venv/bin/gunicorn --workers 3 --bind unix:/run/gunicorn.sock project1.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 2. Daphne (WebSockets)
`sudo nano /etc/systemd/system/daphne.service`
```ini
[Unit]
Description=Daphne ASGI server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/nexuslink
ExecStart=/var/www/nexuslink/venv/bin/daphne -b 0.0.0.0 -p 8001 project1.asgi:application

[Install]
WantedBy=multi-user.target
```

---

## 🌐 Step 5: Nginx & SSL
1. **Nginx Config**:
   `sudo nano /etc/nginx/sites-available/nexuslink`
   ```nginx
   server {
       listen 80;
       server_name your_domain.com; # Add your domain here

       location /ws/ {
           proxy_pass http://0.0.0.0:8001;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/run/gunicorn.sock;
       }
   }
   ```
2. **Enable and Restart**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/nexuslink /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```
3. **SSL (Certbot)**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your_domain.com
   ```

---

## 🚀 Final Check
```bash
python manage.py migrate
python manage.py collectstatic
sudo systemctl daemon-reload
sudo systemctl enable gunicorn daphne
sudo systemctl restart gunicorn daphne
```
Your website is now LIVE on AWS EC2! 🎉
