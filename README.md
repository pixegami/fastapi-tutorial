# FastAPI Tutorial

This is a simple example FastAPI application that pretends to be a bookstore.

# Deploying to AWS EC2

Log into your AWS account and create an EC2 instance (`t2.micro`), using the latest stable
Ubuntu Linux AMI.

[SSH into the instance](https://aws.amazon.com/blogs/compute/new-using-amazon-ec2-instance-connect-for-ssh-access-to-your-ec2-instances/) and run these commands to update the software repository and install
our dependencies.

```bash
sudo apt-get update
sudo apt install python3-pip
sudo apt install nginx  # We'll need this to connect the API to the internet.
```

Add the FastAPI configuration to NGINX's folder.

```bash
cd /etc/nginx/sites-enabled/
```

Create a file called `fastapi_nginx` (like the one in this repository).

```bash
sudo vim fastapi_nginx
```

And put this config into the file (replace the IP address with your EC2 instance's public IP):

```
server {
    listen 80;   
    server_name <YOUR_EC2_IP>;    
    location / {        
        proxy_pass http://127.0.0.1:8000;    
    }
}
```


Start NGINX.

```bash
sudo service nginx restart
```

Start FastAPI.

```bash
python3 -m uvicorn main:app
```

Update EC2 security-group settings for your instance to allow HTTP traffic to port 80.

Now when you visit your public IP of the instance, you should be able to access your API.

# Deploying FastAPI to AWS Lambda

We'll need to modify the API so that it has a Lambda handler. But after that, we can zip
up the dependencies like this:

```bash
pip install -t lib -r requirements.txt
```