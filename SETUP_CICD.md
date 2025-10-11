# CI/CD Pipeline Setup Guide

## Prerequisites
You'll need:
- GitHub account with a repository
- Azure account with an active subscription
- Azure CLI installed locally

## Step 1: GitHub Repository Setup

1. **Create/Use GitHub Repository**
   ```bash
   # If creating new repo
   git init
   git add .
   git commit -m "Initial commit - Django Doctor Appointment System"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

2. **GitHub Personal Access Token**
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Create token with `repo` and `workflow` permissions
   - Save the token securely

## Step 2: Azure Setup

1. **Login to Azure CLI**
   ```bash
   az login
   ```

2. **Get Your Azure Details**
   ```bash
   # Get subscription ID
   az account show --query id -o tsv
   
   # Get tenant ID  
   az account show --query tenantId -o tsv
   ```

3. **Run Azure Deployment Script**
   ```bash
   # Make script executable
   chmod +x deploy-azure.sh
   
   # Run deployment (will prompt for details)
   ./deploy-azure.sh
   ```

## Step 3: Configure GitHub Secrets

After running the Azure script, add these secrets to your GitHub repository:

**Repository Settings > Secrets and variables > Actions > New repository secret**

The deploy script will output the exact values you need to add:

- `AZURE_CREDENTIALS`
- `REGISTRY_LOGIN_SERVER` 
- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`
- `DATABASE_URL`
- `REDIS_URL`

## Step 4: Trigger Deployment

1. **Push to main branch** to trigger the CI/CD pipeline
2. **Monitor the deployment** in GitHub Actions tab
3. **Access your live app** at the URL provided by the deployment script

## Step 5: Verify Deployment

- Check GitHub Actions for successful deployment
- Visit the Azure App Service URL
- Test application functionality
- Verify database connectivity

## Troubleshooting

If deployment fails:
1. Check GitHub Actions logs
2. Verify all secrets are correctly set
3. Check Azure resource status in Azure Portal
4. Review application logs in Azure App Service

## Next Steps After Deployment

- Set up custom domain (optional)
- Configure SSL certificate
- Set up monitoring and alerts
- Configure backup strategies
