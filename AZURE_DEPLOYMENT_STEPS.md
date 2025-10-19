# Azure Deployment Steps

Your code is now on GitHub: https://github.com/joiceantony27/doctor-appointment

## Next: Deploy Azure Infrastructure

### Step 1: Login to Azure
```bash
az login
```

### Step 2: Run Deployment Script
```bash
./deploy-config.sh
```

This will:
- Create Azure resource group
- Deploy PostgreSQL database
- Create Container Registry
- Set up App Service
- Generate GitHub secrets

### Step 3: Add GitHub Secrets
After deployment, add these secrets to your GitHub repository:
- Go to: https://github.com/joiceantony27/doctor-appointment/settings/secrets/actions
- Add the secrets provided by the deployment script

### Step 4: Trigger CI/CD Pipeline
```bash
git commit --allow-empty -m "Trigger Azure deployment"
git push
```

Your app will be live at: `https://[app-name].azurewebsites.net`
