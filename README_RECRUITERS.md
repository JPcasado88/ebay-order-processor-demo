# 🚀 eBay Order Processor - Demo Version for Recruiters


> **Note**: This is a sanitized demo version prepared specifically for recruiting purposes. All sensitive client data, API tokens, and proprietary business logic have been replaced with sample data.
> For login use demo // demo123

## 📋 Project Overview

This is a **production-ready Flask web application** that demonstrates advanced full-stack development skills through automated eBay order processing. The application showcases:

- **Complex API Integration** with eBay's Trading API
- **Advanced Data Processing** with sophisticated SKU matching algorithms
- **Asynchronous Background Processing** for handling long-running tasks
- **Production-Ready Architecture** with proper separation of concerns
- **Modern Web Development Practices** including security and deployment considerations

## 🛠 Technical Highlights

### **Backend Architecture**
- **Flask Application Factory Pattern** for scalable architecture
- **Blueprint-based routing** for modular organization
- **Service Layer Separation** (business logic separate from web layer)
- **Threaded background processing** to prevent request timeouts
- **Real-time progress tracking** via AJAX polling

### **Data Processing Engine**
- **Multi-stage SKU matching algorithm** with 19-case pattern recognition
- **Title-based product analysis** for vehicle make/model/year extraction
- **Complex Excel file generation** with dynamic formatting
- **Batch processing** for multi-item orders

### **Production Features**
- **OAuth2 token management** with automatic refresh
- **File-based process state** for stateless cloud deployment
- **Health check endpoints** for monitoring
- **Scheduled cleanup jobs** using APScheduler
- **Comprehensive logging** and error handling

### **Security & Best Practices**
- **Environment-based configuration** management
- **Password hashing** using Werkzeug security
- **Session-based authentication**
- **Input validation** and sanitization
- **Proper secret management**

## 🔧 Tech Stack

| Category | Technologies |
|----------|-------------|
| **Backend** | Python, Flask, Gunicorn |
| **Data Processing** | Pandas, OpenPyXL |
| **API Integration** | ebay-sdk-python, requests |
| **Background Jobs** | Threading, APScheduler |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+) |
| **Deployment** | Railway, Docker-ready |

## 📁 Demo Data

The following files contain **sample data only**:

- `data/ebay_tokens_demo.json` - Placeholder API tokens
- `data/sample_product_data.csv` - Generic automotive product data
- All output files are demonstrations of the file generation capabilities

## 🚀 Key Features Demonstrated

### 1. **Complex API Integration**
```python
# Sophisticated token management with automatic refresh
def refresh_access_token(self, store_name):
    # Handles OAuth2 token lifecycle
    # Implements retry logic and error handling
```

### 2. **Advanced SKU Matching Algorithm**
```python
def extract_sku_identifier(title, sku):
    # 19-case pattern matching system
    # Handles various SKU formats and edge cases
    # Business-specific logic for product identification
```

### 3. **Background Processing**
```python
# Non-blocking task execution
def start_background_process():
    # Threaded execution prevents UI blocking
    # Real-time progress updates via file-based state
```

### 4. **Tracking Upload System**
```python
# Complete order fulfillment workflow
def process_tracking_upload():
    # Matches courier tracking data to internal order files
    # Supports multiple file formats and encodings
    # Batch processing with audit trail
    # Smart barcode matching with error handling
```

**Business Value**: Completes the order-to-delivery lifecycle by connecting internal order management with external courier systems. Demonstrates complex data matching algorithms and file processing capabilities.

### 5. **Dynamic File Generation**
- Multiple Excel formats (RUN, COURIER_MASTER, Tracking)
- ZIP file creation for batch processing
- Template-based document generation

## 🏗 Architecture Highlights

```
├── ebay_processor/          # Main application package
│   ├── __init__.py         # Application factory
│   ├── config.py           # Environment-based configuration
│   ├── services/           # Business logic layer
│   │   ├── ebay_api.py     # API integration service
│   │   ├── file_service.py # File generation service
│   │   └── sku_matching_service.py # Core matching algorithms
│   └── web/                # Web layer
│       ├── routes.py       # Flask routes (Blueprint)
│       └── utils.py        # Web utilities
```

## 🔒 Security Considerations

- **No hardcoded secrets** - All sensitive data externalized
- **Environment separation** - Development/production configurations
- **Input sanitization** - Protection against injection attacks
- **Session security** - Secure session management
- **API rate limiting** - Respectful API usage patterns

## 🌐 Deployment Ready

- **Procfile** for Platform-as-a-Service deployment
- **requirements.txt** with pinned dependencies
- **Health check endpoint** for load balancer integration
- **Persistent volume support** for stateless deployment
- **Environment variable configuration** for easy deployment

## 📊 Performance Features

- **Asynchronous processing** prevents timeout issues
- **Efficient data structures** for large dataset processing
- **Memory-conscious** file handling for large Excel generation
- **Background cleanup** to prevent disk space issues

## 🎯 Business Value Demonstrated

This project showcases the ability to:

1. **Integrate complex third-party APIs** with proper error handling
2. **Process large datasets efficiently** with custom algorithms
3. **Create production-ready applications** with proper architecture
4. **Handle real-world business requirements** with sophisticated logic
5. **Deploy scalable applications** to cloud platforms
6. **Implement complete business workflows** from order to delivery tracking
7. **Design data integration systems** that connect multiple external services
8. **Build user-friendly interfaces** for complex business processes

---

## 💼 For Recruiters

This demo version maintains all the technical complexity and architectural decisions of the production system while ensuring no proprietary or sensitive information is exposed. The code demonstrates:

- **Senior-level Python development** skills
- **Full-stack web application** expertise
- **Production deployment** experience
- **Complex business logic** implementation
- **API integration** proficiency
- **Modern development practices**

The actual production version processes thousands of orders and generates comprehensive logistics files for a thriving e-commerce operation.

---

*This is a demo version created specifically for recruiting purposes. All sensitive data has been sanitized or replaced with sample data.*

## 🔄 Complete Order Fulfillment Workflow

This application demonstrates a **complete end-to-end order processing system** that handles the entire lifecycle from eBay order to customer delivery tracking:

### **Phase 1: Order Processing** 📊
- Fetches orders from eBay Trading API
- Applies sophisticated SKU matching algorithms (19-case pattern recognition)
- Generates multiple Excel files for different business purposes:
  - **RUN files**: Internal picking and packing
  - **Tracking files**: Customer service and logistics
  - **Courier Master files**: Shipping label generation

### **Phase 2: Logistics Integration** 📦
- Tracking files contain internal barcodes (`Our_Barcode`) but no tracking numbers
- Physical orders are shipped via courier companies
- System generates demo CSV files showing expected courier data format

### **Phase 3: Tracking Upload** 🔗
- **Smart File Detection**: Automatically discovers generated tracking files
- **Format Flexibility**: Accepts CSV uploads in multiple encodings (UTF-8, CP1252, Latin-1)
- **Intelligent Matching**: Maps courier tracking numbers to internal barcodes
- **Batch Processing**: Updates multiple tracking files simultaneously
- **Audit Trail**: Creates versioned backup files with timestamps

### **Phase 4: Complete Records** ✅
- Excel tracking files now contain courier tracking numbers
- Customer service can provide tracking information to customers
- Complete order-to-delivery audit trail maintained

### **Demo Workflow for Recruiters** 🎪
```
1. Process Demo Orders → Generates 8 sample orders across 3 stores
2. Navigate to "Upload Tracking Data" → Auto-detects tracking files
3. Select Demo CSV → Contains realistic tracking numbers
4. Click "Process" → Updates 4 tracking numbers instantly
5. Download Results → See completed tracking files
```

This demonstrates **real-world business process automation** and **complex data integration** skills essential for enterprise applications. 
