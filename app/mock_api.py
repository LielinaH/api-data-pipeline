import random
from datetime import datetime, timedelta
import json

# Lists of dummy data to build realistic records
NAMES = [
    "Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince", "Evan Wright",
    "Fiona Gallagher", "George Clark", "Hannah Abbott", "Ian Malcolm", "Julia Roberts",
    "Kevin Bacon", "Laura Croft", "Michael Scott", "Nina Simone", "Oscar Wilde"
]
PRODUCTS = [
    "Premium Subscription Plan", "Enterprise License Key", "Consulting Hour Block",
    "Developer API Access", "E-Book: Master Automation", "SaaS Analytics Dashboard Addon",
    "Custom Integration Setup"
]
DOMAINS = ["gmail.com", "outlook.com", "company.co", "enterprise.org", "startup.io"]
STATUS_OPTIONS = ["completed", "Completed", "pending", "Pending", "cancelled", "CANCELLED", "invalid_status"]

def generate_mock_orders(count: int = 25) -> list:
    """
    Generates a list of simulated orders.
    A portion of these orders will intentionally contain anomalies/errors
    to test the pipeline's filtering, cleaning, and validation capabilities.
    """
    orders = []
    
    # We will generate a base set of standard order IDs
    # To create realistic duplicate errors, we'll occasionally reuse an ID
    existing_ids = [f"ORD-{random.randint(10000, 99999)}" for _ in range(count)]
    
    for i in range(count):
        # Determine if this record should be an anomaly
        is_anomaly = random.random() < 0.25  # 25% chance of containing an anomaly
        
        # Base valid values
        order_id = existing_ids[i]
        customer_name = random.choice(NAMES)
        # Standard email
        customer_email = f"{customer_name.lower().replace(' ', '.')}@{random.choice(DOMAINS)}"
        product_name = random.choice(PRODUCTS)
        price = round(random.uniform(19.99, 499.99), 2)
        quantity = random.randint(1, 5)
        total_amount = round(price * quantity, 2)
        
        # Order date within the last 30 days
        days_ago = random.randint(0, 30)
        order_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
        status = random.choice(["COMPLETED", "PENDING", "CANCELLED"])
        
        # Inject anomalies
        if is_anomaly:
            anomaly_type = random.choice([
                "duplicate_id",
                "missing_name",
                "invalid_email",
                "negative_price",
                "string_price",
                "negative_qty",
                "future_date",
                "mismatched_total",
                "non_standard_status",
                "empty_record"
            ])
            
            if anomaly_type == "duplicate_id":
                # Reuse an order_id from an earlier record in the list (if index > 0)
                if i > 0:
                    order_id = orders[random.randint(0, i - 1)]["order_id"]
                    
            elif anomaly_type == "missing_name":
                customer_name = ""  # Empty string
                
            elif anomaly_type == "invalid_email":
                # Malformed emails
                customer_email = random.choice([
                    "bad_email_no_at.com",
                    "spaces in@domain.com",
                    "user@",
                    "@domain.com",
                    "missing_tld@domain."
                ])
                
            elif anomaly_type == "negative_price":
                price = -99.99
                total_amount = price * quantity
                
            elif anomaly_type == "string_price":
                # Price passed as a formatted string rather than float
                price = f"${price}"  # e.g., "$129.99"
                total_amount = f"${total_amount}"
                
            elif anomaly_type == "negative_qty":
                quantity = -1
                
            elif anomaly_type == "future_date":
                # Future date (5 days from now)
                order_date = (datetime.now() + timedelta(days=5)).isoformat()
                
            elif anomaly_type == "mismatched_total":
                # Total amount doesn't match price * quantity
                total_amount = round(price * quantity * 1.5, 2)
                
            elif anomaly_type == "non_standard_status":
                status = random.choice(STATUS_OPTIONS)
                
            elif anomaly_type == "empty_record":
                # Completely null/empty fields
                customer_name = None
                customer_email = None
                
        # Build raw dict
        record = {
            "order_id": order_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "product_name": product_name,
            "price": price,
            "quantity": quantity,
            "total_amount": total_amount,
            "order_date": order_date,
            "status": status
        }
        orders.append(record)
        
    return orders

if __name__ == "__main__":
    # Print sample data when executed directly
    sample_data = generate_mock_orders(5)
    print(json.dumps(sample_data, indent=2))
