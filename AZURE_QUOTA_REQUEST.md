# Azure Quota Request for Django Doctor Appointment System

## Request Details

**Subscription**: Azure for Students  
**Subscription ID**: 9cd25345-5e9f-4b34-b5fd-3e90f767fd41  
**Location**: West US 2  

## Required Quotas

### 1. App Service Plan (Primary Need)
- **Current Limit**: 0 Free VMs
- **Requested Limit**: 1 Free VM
- **Justification**: Educational project - Django Doctor Appointment System with CI/CD pipeline

### 2. Container Instances (Alternative)
- **Service**: Microsoft.ContainerInstance
- **Current Status**: Registered but may need quota
- **Requested Limit**: 1 Container Group

## Business Justification

This is an educational project to demonstrate:
- Django web application development
- Docker containerization
- CI/CD pipeline with GitHub Actions
- Cloud deployment best practices
- DevOps automation

The application is a doctor appointment booking system with:
- User authentication
- Medical specializations
- Appointment scheduling
- Payment processing
- Admin dashboard

## Technical Requirements

- **Runtime**: Python 3.9 Django application
- **Database**: PostgreSQL (can use Azure Database for PostgreSQL)
- **Caching**: Redis (can use Azure Cache for Redis)
- **Container Registry**: Already created (doctorapp6408dbregistry)
- **Resource Group**: Already created (rg-doctor-appointment-prod)

## Request Priority

**High Priority** - This is for educational purposes under Azure for Students program.

## Contact Information

- **Email**: Joice.antony.007@gmail.com
- **GitHub Repository**: https://github.com/joiceantony27/doctor-appointment
- **Project Type**: Educational/Learning

---

## How to Submit This Request

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Help + support** → **New support request**
3. Select **Service and subscription limits (quotas)**
4. Choose your subscription: **Azure for Students**
5. Select **Compute-VM (cores-vCPUs) subscription limit increases**
6. Fill in the details above
7. Submit the request

**Expected Response Time**: 1-3 business days
