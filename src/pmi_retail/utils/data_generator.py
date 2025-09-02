"""
Generalized Retail Data Generator for Workshop
Creates realistic retail execution data with proper account hierarchy
"""

import pandas as pd
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import sys
from pathlib import Path

# Package imports are now handled by the package structure
from pmi_retail.database.snowflake.connection import SnowflakeManager
from pmi_retail.config import settings


class RetailDataGenerator:
    """
    Generates realistic retail execution sample data
    
    Features:
    - Account hierarchy (Chain -> Regional -> Store)
    - Diverse product categories 
    - Realistic transaction patterns
    - Loyalty program data
    - Configurable data scale
    """
    
    def __init__(self, sf_manager: SnowflakeManager, scale: str = "small"):
        self.sf = sf_manager
        self.scale = scale
        
        # Configure data volumes based on scale
        self.data_config = {
            "small": {
                "accounts": 30,
                "products": 20, 
                "months_history": 3,
                "transactions_per_account": (10, 50),
                "loyalty_coverage": 0.6  # 60% of accounts have loyalty members
            },
            "medium": {
                "accounts": 100,
                "products": 50,
                "months_history": 6,
                "transactions_per_account": (20, 100),
                "loyalty_coverage": 0.7
            },
            "large": {
                "accounts": 500,
                "products": 200,
                "months_history": 12,
                "transactions_per_account": (50, 200),
                "loyalty_coverage": 0.8
            }
        }
        
        self.config = self.data_config[scale]
        
        # Retail data reference lists
        self.chain_names = [
            "Metro Markets", "City Express", "Prime Retail", "Quick Stop", "Corner Store",
            "Valley Markets", "Summit Stores", "Riverside Retail", "Downtown Markets", "Uptown Express"
        ]
        
        self.store_names = [
            "Main Street", "Oak Avenue", "Pine Plaza", "Elm Center", "First Street",
            "Broadway", "Park Avenue", "Second Street", "Third Avenue", "Central Plaza",
            "Northside", "Southgate", "Westfield", "Eastside", "Midtown"
        ]
        
        self.cities = [
            ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"), ("Houston", "TX"),
            ("Phoenix", "AZ"), ("Philadelphia", "PA"), ("San Antonio", "TX"), ("San Diego", "CA"),
            ("Dallas", "TX"), ("San Jose", "CA"), ("Austin", "TX"), ("Jacksonville", "FL"),
            ("Fort Worth", "TX"), ("Columbus", "OH"), ("Charlotte", "NC"), ("San Francisco", "CA"),
            ("Indianapolis", "IN"), ("Seattle", "WA"), ("Denver", "CO"), ("Washington", "DC"),
            ("Boston", "MA"), ("El Paso", "TX"), ("Detroit", "MI"), ("Nashville", "TN"),
            ("Portland", "OR"), ("Memphis", "TN"), ("Oklahoma City", "OK"), ("Las Vegas", "NV")
        ]
        
        # General retail product categories (non-specific)
        self.product_categories = {
            "Beverages": {
                "subcategories": ["Soft Drinks", "Energy Drinks", "Juices", "Water", "Coffee/Tea"],
                "brands": ["Premium Brand", "Standard Brand", "Value Brand", "Local Brand"],
                "price_range": (1.99, 8.99)
            },
            "Snacks": {
                "subcategories": ["Chips", "Crackers", "Nuts", "Candy", "Cookies"],
                "brands": ["Crispy Co", "Snack Master", "Golden Treats", "Quick Bite"],
                "price_range": (2.49, 12.99)
            },
            "Personal Care": {
                "subcategories": ["Oral Care", "Hair Care", "Skin Care", "Deodorants"],
                "brands": ["Care Plus", "Daily Fresh", "Pure Life", "Essential"],
                "price_range": (3.99, 24.99)
            },
            "Household": {
                "subcategories": ["Cleaning", "Paper Products", "Laundry", "Air Care"],
                "brands": ["Clean Home", "Sparkle", "Fresh Air", "Daily Use"],
                "price_range": (4.99, 19.99)
            },
            "Food": {
                "subcategories": ["Frozen", "Canned", "Packaged", "Bakery", "Dairy"],
                "brands": ["Farm Fresh", "Home Style", "Quick Meal", "Natural Choice"],
                "price_range": (2.99, 15.99)
            }
        }
        
        self.segments = ["Premium", "Standard", "Basic"]
        self.loyalty_tiers = ["Bronze", "Silver", "Gold", "Platinum"]
        self.order_sources = ["In-Store", "Online", "Mobile App", "Phone", "Kiosk"]
        self.sales_reps = [
            "Sarah Johnson", "Mike Chen", "Lisa Rodriguez", "David Kim", "Jennifer Wilson",
            "Robert Brown", "Amanda Davis", "James Garcia", "Maria Lopez", "Kevin Thompson"
        ]
        
        # Contact generation data
        self.first_names = [
            "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
            "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
            "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa",
            "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna",
            "Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
            "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
            "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
            "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill"
        ]
        
        self.job_titles = [
            "Customer", "Student", "Professional", "Retiree", "Entrepreneur", "Manager",
            "Consultant", "Analyst", "Coordinator", "Specialist", "Director", "Supervisor"
        ]
    
    def generate_accounts_with_hierarchy(self) -> pd.DataFrame:
        """Generate accounts with realistic retail hierarchy"""
        logger.info(f"Generating {self.config['accounts']} accounts with hierarchy...")
        
        accounts = []
        account_id_counter = 1
        
        # Step 1: Create parent companies/chains (about 20% of total)
        num_chains = max(3, self.config['accounts'] // 5)
        
        for i in range(num_chains):
            chain_name = self.chain_names[i % len(self.chain_names)]
            city, state = random.choice(self.cities)
            
            account = {
                'ACCOUNT_ID': f'ACC{str(account_id_counter).zfill(4)}',
                'ACCOUNT_NAME': f'{chain_name} Corp',
                'PARENT_ACCOUNT_ID': None,
                'ACCOUNT_TYPE': 'Chain Headquarters',
                'SEGMENT': random.choice(['Premium', 'Standard']),  # Chains usually not Basic
                'ADDRESS': f'{random.randint(100, 9999)} {random.choice(["Corporate", "Executive", "Business"])} Blvd',
                'CITY': city,
                'STATE': state,
                'ZIP_CODE': f'{random.randint(10000, 99999)}',
                'COUNTRY': 'USA',
                'PHONE': f'({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}',
                'EMAIL': f'corporate@{chain_name.lower().replace(" ", "").replace("markets", "").replace("stores", "").replace("retail", "").replace("express", "")}corp.com',
                'REGISTRATION_DATE': (datetime.now() - timedelta(days=random.randint(1095, 3650))).date(),
                'STATUS': 'Active',
                'HIERARCHY_LEVEL': 1,
                'ANNUAL_REVENUE': random.randint(50000000, 500000000),  # Large chains
                'EMPLOYEE_COUNT': random.randint(1000, 50000)
            }
            accounts.append(account)
            account_id_counter += 1
        
        # Step 2: Create regional offices (about 30% of remaining)
        chain_ids = [acc['ACCOUNT_ID'] for acc in accounts]
        num_regional = max(5, (self.config['accounts'] - num_chains) // 3)
        
        for i in range(num_regional):
            parent_chain_id = random.choice(chain_ids)
            parent_chain = next(acc for acc in accounts if acc['ACCOUNT_ID'] == parent_chain_id)
            
            city, state = random.choice(self.cities)
            region_name = random.choice(['Northeast', 'Southeast', 'Midwest', 'Southwest', 'West Coast', 'Central'])
            
            account = {
                'ACCOUNT_ID': f'ACC{str(account_id_counter).zfill(4)}',
                'ACCOUNT_NAME': f'{parent_chain["ACCOUNT_NAME"].replace(" Corp", "")} {region_name} Region',
                'PARENT_ACCOUNT_ID': parent_chain_id,
                'ACCOUNT_TYPE': 'Regional Office',
                'SEGMENT': parent_chain['SEGMENT'],  # Inherit from parent
                'ADDRESS': f'{random.randint(100, 9999)} {random.choice(["Regional", "District", "Area"])} Dr',
                'CITY': city,
                'STATE': state,
                'ZIP_CODE': f'{random.randint(10000, 99999)}',
                'COUNTRY': 'USA',
                'PHONE': f'({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}',
                'EMAIL': f'{region_name.lower().replace(" ", "")}@{parent_chain["EMAIL"].split("@")[1]}',
                'REGISTRATION_DATE': (datetime.now() - timedelta(days=random.randint(365, 2190))).date(),
                'STATUS': 'Active',
                'HIERARCHY_LEVEL': 2,
                'ANNUAL_REVENUE': random.randint(5000000, 50000000),  # Regional revenue
                'EMPLOYEE_COUNT': random.randint(100, 2000)
            }
            accounts.append(account)
            account_id_counter += 1
        
        # Step 3: Create individual stores (remaining accounts)
        parent_ids = [acc['ACCOUNT_ID'] for acc in accounts]  # Can be chain or regional
        remaining_accounts = self.config['accounts'] - len(accounts)
        
        for i in range(remaining_accounts):
            # 70% chance to have a parent, 30% independent
            if random.random() < 0.7 and parent_ids:
                parent_id = random.choice(parent_ids)
                parent_account = next(acc for acc in accounts if acc['ACCOUNT_ID'] == parent_id)
                
                # Determine hierarchy level
                hierarchy_level = parent_account['HIERARCHY_LEVEL'] + 1
                if hierarchy_level > 3:  # Max 3 levels
                    hierarchy_level = 3
                
                account_type = 'Store' if parent_account['ACCOUNT_TYPE'] in ['Chain Headquarters', 'Regional Office'] else 'Franchise'
                
                # Use parent's chain name for consistency
                if 'Corp' in parent_account['ACCOUNT_NAME']:
                    base_name = parent_account['ACCOUNT_NAME'].replace(' Corp', '').replace(' Region', '').replace(' Northeast', '').replace(' Southeast', '').replace(' Midwest', '').replace(' Southwest', '').replace(' West Coast', '').replace(' Central', '')
                else:
                    base_name = parent_account['ACCOUNT_NAME'].split()[0]
                
                segment = parent_account['SEGMENT']  # Inherit segment
                
            else:
                # Independent store
                parent_id = None
                hierarchy_level = 1
                account_type = 'Independent'
                base_name = random.choice(self.store_names)
                segment = random.choice(self.segments)
            
            city, state = random.choice(self.cities)
            store_location = random.choice(self.store_names)
            
            account = {
                'ACCOUNT_ID': f'ACC{str(account_id_counter).zfill(4)}',
                'ACCOUNT_NAME': f'{base_name} {store_location}' if parent_id else f'{store_location} Market',
                'PARENT_ACCOUNT_ID': parent_id,
                'ACCOUNT_TYPE': account_type,
                'SEGMENT': segment,
                'ADDRESS': f'{random.randint(100, 9999)} {store_location} {random.choice(["St", "Ave", "Blvd", "Dr", "Way"])}',
                'CITY': city,
                'STATE': state,
                'ZIP_CODE': f'{random.randint(10000, 99999)}',
                'COUNTRY': 'USA',
                'PHONE': f'({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}',
                'EMAIL': f'store{account_id_counter}@{base_name.lower().replace(" ", "")}retail.com',
                'REGISTRATION_DATE': (datetime.now() - timedelta(days=random.randint(30, 1825))).date(),
                'STATUS': 'Active',
                'HIERARCHY_LEVEL': hierarchy_level,
                'ANNUAL_REVENUE': random.randint(500000, 10000000) if account_type != 'Independent' else random.randint(100000, 2000000),
                'EMPLOYEE_COUNT': random.randint(5, 200) if account_type != 'Independent' else random.randint(3, 50)
            }
            accounts.append(account)
            account_id_counter += 1
        
        df = pd.DataFrame(accounts)
        
        # Convert date columns to proper SQL date strings
        if 'REGISTRATION_DATE' in df.columns:
            df['REGISTRATION_DATE'] = df['REGISTRATION_DATE'].astype(str)
        
        # Log hierarchy stats
        hierarchy_stats = df.groupby(['HIERARCHY_LEVEL', 'ACCOUNT_TYPE']).size().to_dict()
        logger.info(f"Account hierarchy created: {hierarchy_stats}")
        
        return df
    
    def generate_products(self) -> pd.DataFrame:
        """Generate diverse retail products"""
        logger.info(f"Generating {self.config['products']} products...")
        
        products = []
        product_id_counter = 1
        
        # Calculate products per category
        products_per_category = self.config['products'] // len(self.product_categories)
        
        for category, category_data in self.product_categories.items():
            for i in range(products_per_category):
                subcategory = random.choice(category_data['subcategories'])
                brand = random.choice(category_data['brands'])
                price_min, price_max = category_data['price_range']
                
                # Generate product variants
                variants = ['Regular', 'Large', 'Family', 'Travel', 'Premium', 'Value', 'Multi-pack']
                variant = random.choice(variants)
                
                product = {
                    'PRODUCT_ID': f'PRD{str(product_id_counter).zfill(4)}',
                    'PRODUCT_NAME': f'{brand} {subcategory} {variant}',
                    'CATEGORY': category,
                    'SUBCATEGORY': subcategory,
                    'BRAND': brand,
                    'UNIT_PRICE': round(random.uniform(price_min, price_max), 2),
                    'COST_PRICE': round(random.uniform(price_min * 0.4, price_min * 0.7), 2),  # 40-70% margin
                    'LAUNCH_DATE': (datetime.now() - timedelta(days=random.randint(30, 1095))).date(),
                    'STATUS': 'Active',
                    'PRODUCT_DESCRIPTION': f'High-quality {subcategory.lower()} from {brand}',
                    'IS_NEW_PRODUCT': random.random() < 0.15,  # 15% are new products
                    'TARGET_SEGMENT': random.choice(self.segments)
                }
                products.append(product)
                product_id_counter += 1
        
        # Fill remaining products if any
        while len(products) < self.config['products']:
            category = random.choice(list(self.product_categories.keys()))
            category_data = self.product_categories[category]
            subcategory = random.choice(category_data['subcategories'])
            brand = random.choice(category_data['brands'])
            price_min, price_max = category_data['price_range']
            
            product = {
                'PRODUCT_ID': f'PRD{str(product_id_counter).zfill(4)}',
                'PRODUCT_NAME': f'{brand} {subcategory} Special',
                'CATEGORY': category,
                'SUBCATEGORY': subcategory,
                'BRAND': brand,
                'UNIT_PRICE': round(random.uniform(price_min, price_max), 2),
                'COST_PRICE': round(random.uniform(price_min * 0.4, price_min * 0.7), 2),
                'LAUNCH_DATE': (datetime.now() - timedelta(days=random.randint(30, 730))).date(),
                'STATUS': 'Active',
                'PRODUCT_DESCRIPTION': f'Quality {subcategory.lower()} product',
                'IS_NEW_PRODUCT': random.random() < 0.1,
                'TARGET_SEGMENT': random.choice(self.segments)
            }
            products.append(product)
            product_id_counter += 1
        
        df = pd.DataFrame(products)
        
        # Convert date columns to proper SQL date strings
        if 'LAUNCH_DATE' in df.columns:
            df['LAUNCH_DATE'] = df['LAUNCH_DATE'].astype(str)
        
        # Log product stats
        category_stats = df['CATEGORY'].value_counts().to_dict()
        logger.info(f"Products by category: {category_stats}")
        
        return df
    
    def generate_transactions(self, accounts_df: pd.DataFrame, products_df: pd.DataFrame, contacts_df: pd.DataFrame, campaigns_df: pd.DataFrame) -> pd.DataFrame:
        """Generate realistic transaction data"""
        logger.info("Generating transaction data...")
        
        transactions = []
        transaction_id_counter = 1
        
        # Get only store-level accounts (hierarchy level 2 or 3, or independent)
        store_accounts = accounts_df[
            (accounts_df['HIERARCHY_LEVEL'] >= 2) | 
            (accounts_df['ACCOUNT_TYPE'] == 'Independent')
        ]
        
        account_ids = store_accounts['ACCOUNT_ID'].tolist()
        product_ids = products_df['PRODUCT_ID'].tolist()
        
        # Generate transactions over the specified months
        start_date = datetime.now() - timedelta(days=self.config['months_history'] * 30)
        end_date = datetime.now()
        
        for account_id in account_ids:
            account = store_accounts[store_accounts['ACCOUNT_ID'] == account_id].iloc[0]
            
            # Number of transactions based on account segment and type
            min_trans, max_trans = self.config['transactions_per_account']
            
            # Adjust based on segment
            if account['SEGMENT'] == 'Premium':
                max_trans = int(max_trans * 1.5)
            elif account['SEGMENT'] == 'Basic':
                max_trans = int(max_trans * 0.7)
            
            num_transactions = random.randint(min_trans, max_trans)
            
            for _ in range(num_transactions):
                # Random transaction date
                transaction_date = start_date + timedelta(
                    days=random.randint(0, (end_date - start_date).days)
                )
                
                # Select product (some products more popular than others)
                product_id = random.choice(product_ids)
                product = products_df[products_df['PRODUCT_ID'] == product_id].iloc[0]
                
                # Assign contact ID (70% chance to have a contact)
                contact_id = None
                if random.random() < 0.7 and len(contacts_df) > 0:
                    contact_id = random.choice(contacts_df['CONTACT_ID'].tolist())
                
                # Assign campaign ID (40% chance to be campaign-driven)
                campaign_id = None
                if random.random() < 0.4 and len(campaigns_df) > 0:
                    # Filter for active campaigns that target this account/product
                    active_campaigns = campaigns_df[campaigns_df['STATUS'] == 'Active']
                    if len(active_campaigns) > 0:
                        campaign_id = random.choice(active_campaigns['CAMPAIGN_ID'].tolist())
                
                # Quantity based on product category
                if product['CATEGORY'] in ['Beverages', 'Snacks']:
                    quantity = random.randint(1, 50)  # High volume items
                elif product['CATEGORY'] == 'Personal Care':
                    quantity = random.randint(1, 10)  # Medium volume
                else:
                    quantity = random.randint(1, 20)  # Variable volume
                
                # Price with some variation
                base_price = product['UNIT_PRICE']
                unit_price = base_price * random.uniform(0.85, 1.15)  # ±15% price variation
                total_amount = quantity * unit_price
                
                # Discount (more likely for premium accounts)
                discount_rate = 0
                if account['SEGMENT'] == 'Premium':
                    discount_rate = random.uniform(0, 0.15)  # Up to 15% discount
                elif account['SEGMENT'] == 'Standard':
                    discount_rate = random.uniform(0, 0.08)  # Up to 8% discount
                else:
                    discount_rate = random.uniform(0, 0.05)  # Up to 5% discount
                
                discount_amount = total_amount * discount_rate
                net_amount = total_amount - discount_amount
                
                transaction = {
                    'TRANSACTION_ID': f'TXN{str(transaction_id_counter).zfill(6)}',
                    'ACCOUNT_ID': account_id,
                    'CONTACT_ID': contact_id,
                    'PRODUCT_ID': product_id,
                    'CAMPAIGN_ID': campaign_id,
                    'TRANSACTION_DATE': transaction_date.date(),
                    'QUANTITY': quantity,
                    'UNIT_PRICE': round(unit_price, 2),
                    'TOTAL_AMOUNT': round(total_amount, 2),
                    'DISCOUNT_AMOUNT': round(discount_amount, 2),
                    'NET_AMOUNT': round(net_amount, 2),
                    'SALES_REP': random.choice(self.sales_reps),
                    'ORDER_SOURCE': random.choice(self.order_sources)
                }
                transactions.append(transaction)
                transaction_id_counter += 1
        
        df = pd.DataFrame(transactions)
        
        # Convert date columns to proper SQL date strings
        if 'TRANSACTION_DATE' in df.columns:
            df['TRANSACTION_DATE'] = df['TRANSACTION_DATE'].astype(str)
        
        # Log transaction stats
        total_revenue = df['NET_AMOUNT'].sum()
        avg_transaction = df['NET_AMOUNT'].mean()
        logger.info(f"Generated {len(df):,} transactions, Total Revenue: ${total_revenue:,.2f}, Avg: ${avg_transaction:.2f}")
        
        return df
    
    def generate_loyalty_members(self, accounts_df: pd.DataFrame, contacts_df: pd.DataFrame) -> pd.DataFrame:
        """Generate loyalty program members"""
        logger.info("Generating loyalty members...")
        
        members = []
        member_id_counter = 1
        
        # Get store-level accounts
        store_accounts = accounts_df[
            (accounts_df['HIERARCHY_LEVEL'] >= 2) | 
            (accounts_df['ACCOUNT_TYPE'] == 'Independent')
        ]
        
        # Only some accounts have loyalty programs (based on coverage rate)
        num_accounts_with_loyalty = int(len(store_accounts) * self.config['loyalty_coverage'])
        loyalty_accounts = store_accounts.sample(n=num_accounts_with_loyalty)
        
        for _, account in loyalty_accounts.iterrows():
            # Number of loyalty members per account (based on segment)
            if account['SEGMENT'] == 'Premium':
                num_members = random.randint(50, 200)
            elif account['SEGMENT'] == 'Standard':
                num_members = random.randint(20, 100)
            else:
                num_members = random.randint(5, 50)
            
            for i in range(num_members):
                # Member details
                first_names = ['John', 'Sarah', 'Mike', 'Lisa', 'David', 'Jennifer', 'Robert', 'Amanda', 'James', 'Maria']
                last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
                
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                
                # Loyalty tier based on tenure and activity
                join_date = datetime.now() - timedelta(days=random.randint(30, 1095))
                tenure_days = (datetime.now() - join_date).days
                
                if tenure_days > 730:  # 2+ years
                    tier_weights = {'Bronze': 0.2, 'Silver': 0.3, 'Gold': 0.3, 'Platinum': 0.2}
                elif tenure_days > 365:  # 1+ years
                    tier_weights = {'Bronze': 0.3, 'Silver': 0.4, 'Gold': 0.2, 'Platinum': 0.1}
                else:  # New members
                    tier_weights = {'Bronze': 0.6, 'Silver': 0.3, 'Gold': 0.1, 'Platinum': 0.0}
                
                loyalty_tier = random.choices(
                    list(tier_weights.keys()),
                    weights=list(tier_weights.values())
                )[0]
                
                # Points based on tier
                tier_points = {
                    'Bronze': (0, 500),
                    'Silver': (500, 2000),
                    'Gold': (2000, 5000),
                    'Platinum': (5000, 15000)
                }
                
                points_balance = random.randint(*tier_points[loyalty_tier])
                lifetime_points = int(points_balance * random.uniform(1.2, 3.0))  # More lifetime than current
                
                # Last activity
                last_activity = datetime.now() - timedelta(days=random.randint(1, 90))
                
                # Assign contact ID (80% chance to have a contact)
                contact_id = None
                if random.random() < 0.8 and len(contacts_df) > 0:
                    contact_id = random.choice(contacts_df['CONTACT_ID'].tolist())
                
                member = {
                    'MEMBER_ID': f'MBR{str(member_id_counter).zfill(6)}',
                    'ACCOUNT_ID': account['ACCOUNT_ID'],
                    'CONTACT_ID': contact_id,
                    'MEMBER_EMAIL': f'{first_name.lower()}.{last_name.lower()}@email.com',
                    'MEMBER_PHONE': f'({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}',
                    'LOYALTY_TIER': loyalty_tier,
                    'POINTS_BALANCE': points_balance,
                    'LIFETIME_POINTS': lifetime_points,
                    'JOIN_DATE': join_date.date(),
                    'LAST_ACTIVITY_DATE': last_activity.date(),
                    'STATUS': 'Active' if random.random() > 0.05 else 'Inactive',  # 95% active
                    'PREFERRED_CONTACT': random.choice(['Email', 'Phone', 'SMS'])
                }
                members.append(member)
                member_id_counter += 1
        
        df = pd.DataFrame(members)
        
        # Convert date columns to proper SQL date strings
        if 'JOIN_DATE' in df.columns:
            df['JOIN_DATE'] = df['JOIN_DATE'].astype(str)
        if 'LAST_ACTIVITY_DATE' in df.columns:
            df['LAST_ACTIVITY_DATE'] = df['LAST_ACTIVITY_DATE'].astype(str)
        
        # Log loyalty stats
        tier_stats = df['LOYALTY_TIER'].value_counts().to_dict()
        avg_points = df['POINTS_BALANCE'].mean()
        logger.info(f"Generated {len(df):,} loyalty members, Avg Points: {avg_points:.0f}, Tiers: {tier_stats}")
        
        return df
    
    def generate_contacts(self, accounts_df: pd.DataFrame) -> pd.DataFrame:
        """Generate realistic consumer contacts with optional account relationships"""
        logger.info(f"Generating consumer contacts...")
        
        contacts = []
        contact_id_counter = 1
        
        # Generate more contacts than accounts (some independent, some linked)
        num_contacts = int(self.config['accounts'] * 1.5)  # 50% more contacts than accounts
        
        for i in range(num_contacts):
            first_name = random.choice(self.first_names)
            last_name = random.choice(self.last_names)
            
            # Generate realistic email
            email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@{random.choice(email_domains)}"
            
            # Generate phone numbers
            phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
            mobile = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
            
            # 70% chance to be linked to an account, 30% independent
            account_id = None
            if random.random() < 0.7 and len(accounts_df) > 0:
                account_row = accounts_df.sample(n=1).iloc[0]
                account_id = account_row['ACCOUNT_ID']
            
            # Generate address (some contacts may not have full address)
            has_address = random.random() < 0.8
            city, state = random.choice(self.cities) if has_address else ("", "")
            
            contact = {
                'CONTACT_ID': f'CON{str(contact_id_counter).zfill(4)}',
                'FIRST_NAME': first_name,
                'LAST_NAME': last_name,
                'EMAIL': email,
                'PHONE': phone if random.random() < 0.6 else None,
                'MOBILE_PHONE': mobile if random.random() < 0.8 else None,
                'CONTACT_TYPE': 'Consumer',
                'ACCOUNT_ID': account_id,
                'JOB_TITLE': random.choice(self.job_titles) if random.random() < 0.4 else None,
                'DEPARTMENT': None,  # Consumers typically don't have departments
                'ADDRESS_LINE1': f'{random.randint(100, 9999)} {random.choice(["Main", "Oak", "Pine", "Elm", "First"])} St' if has_address else None,
                'ADDRESS_LINE2': f'Apt {random.randint(1, 999)}' if has_address and random.random() < 0.3 else None,
                'CITY': city if has_address else None,
                'STATE': state if has_address else None,
                'ZIP_CODE': f'{random.randint(10000, 99999)}' if has_address else None,
                'COUNTRY': 'USA' if has_address else None,
                'DATE_OF_BIRTH': (datetime.now() - timedelta(days=random.randint(6570, 25550))).date() if random.random() < 0.7 else None,  # 18-70 years old
                'GENDER': random.choice(['Male', 'Female', 'Other']) if random.random() < 0.6 else None,
                'PREFERRED_CONTACT_METHOD': random.choice(['Email', 'Phone', 'SMS']),
                'MARKETING_OPT_IN': random.choice([True, False]),
                'STATUS': 'Active',
                'CREATED_TIMESTAMP': datetime.now(),
                'UPDATED_TIMESTAMP': datetime.now()
            }
            
            contacts.append(contact)
            contact_id_counter += 1
        
        df = pd.DataFrame(contacts)
        
        # Convert date columns to proper SQL date strings
        if 'DATE_OF_BIRTH' in df.columns:
            df['DATE_OF_BIRTH'] = df['DATE_OF_BIRTH'].astype(str)
        if 'CREATED_TIMESTAMP' in df.columns:
            df['CREATED_TIMESTAMP'] = df['CREATED_TIMESTAMP'].astype(str)
        if 'UPDATED_TIMESTAMP' in df.columns:
            df['UPDATED_TIMESTAMP'] = df['UPDATED_TIMESTAMP'].astype(str)
        
        # Log contact stats
        linked_count = df['ACCOUNT_ID'].notna().sum()
        independent_count = len(df) - linked_count
        logger.info(f"Generated {len(df):,} contacts: {linked_count:,} linked to accounts, {independent_count:,} independent")
        
        return df
    
    def generate_notes(self, accounts_df: pd.DataFrame, contacts_df: pd.DataFrame) -> pd.DataFrame:
        """Generate realistic notes with time-bound fields"""
        logger.info(f"Generating sample notes...")
        
        notes = []
        note_id_counter = 1
        
        # Note types and categories
        note_types = ['Contact Note', 'Account Note', 'General Note']
        note_categories = ['Customer Service', 'Sales', 'Support', 'General', 'Follow-up', 'Issue Resolution']
        note_priorities = ['Low', 'Medium', 'High', 'Critical']
        note_statuses = ['Active', 'Resolved', 'Archived']
        
        # Sample note subjects and content
        note_subjects = [
            'Customer inquiry about product availability',
            'Follow-up call scheduled',
            'Account review meeting notes',
            'Support ticket resolution',
            'Sales opportunity identified',
            'Customer feedback received',
            'Account status update',
            'Service request details',
            'Meeting summary',
            'Action items from call'
        ]
        
        note_content_samples = [
            'Customer called to inquire about bulk pricing for product line. Discussed volume discounts and delivery options.',
            'Follow-up call scheduled for next week to discuss new product launch and potential partnership opportunities.',
            'Account review meeting completed. Customer satisfied with current service level. Discussed expansion plans.',
            'Support ticket resolved. Customer issue was related to account access. Provided new login credentials.',
            'Sales opportunity identified during quarterly business review. Customer interested in premium tier upgrade.',
            'Customer provided positive feedback about recent service improvements. Will use as case study.',
            'Account status updated to reflect new contract terms. All stakeholders notified of changes.',
            'Service request details documented. Customer needs technical assistance with platform integration.',
            'Meeting summary: Discussed Q4 goals, identified key challenges, and agreed on next steps.',
            'Action items from call: Schedule demo, prepare proposal, follow up on pricing questions.'
        ]
        
        # Generate notes
        num_notes = int(len(contacts_df) * 0.8) + int(len(accounts_df) * 0.6)  # Mix of contact and account notes
        
        for i in range(num_notes):
            note_type = random.choice(note_types)
            note_category = random.choice(note_categories)
            note_priority = random.choice(note_priorities)
            note_status = random.choice(note_statuses)
            
            # Determine if note is for contact, account, or general
            contact_id = None
            account_id = None
            
            if note_type == 'Contact Note' and len(contacts_df) > 0:
                contact_id = random.choice(contacts_df['CONTACT_ID'].tolist())
                # If contact has account, link to that account too
                contact_row = contacts_df[contacts_df['CONTACT_ID'] == contact_id].iloc[0]
                if contact_row['ACCOUNT_ID']:
                    account_id = contact_row['ACCOUNT_ID']
            elif note_type == 'Account Note' and len(accounts_df) > 0:
                account_id = random.choice(accounts_df['ACCOUNT_ID'].tolist())
            # General notes can have both or neither
            
            # Generate time-bound fields
            created_date = datetime.now() - timedelta(days=random.randint(1, 365))
            effective_start = created_date.date()
            
            # 70% of notes have effective end dates
            effective_end = None
            if random.random() < 0.7:
                effective_end = effective_start + timedelta(days=random.randint(30, 365))
            
            # Due date for active notes (not resolved)
            due_date = None
            if note_status == 'Active' and random.random() < 0.6:
                due_date = datetime.now().date() + timedelta(days=random.randint(1, 30))
            
            # Resolution date for resolved notes
            resolution_date = None
            if note_status == 'Resolved':
                resolution_date = effective_start + timedelta(days=random.randint(1, 30))
            
            # Select note content
            subject_idx = random.randint(0, len(note_subjects) - 1)
            subject = note_subjects[subject_idx]
            note_text = note_content_samples[subject_idx]
            
            note = {
                'NOTE_ID': f'NOTE{str(note_id_counter).zfill(4)}',
                'NOTE_TYPE': note_type,
                'NOTE_CATEGORY': note_category,
                'NOTE_PRIORITY': note_priority,
                'NOTE_STATUS': note_status,
                'SUBJECT': subject,
                'NOTE_TEXT': note_text,
                'CONTACT_ID': contact_id,
                'ACCOUNT_ID': account_id,
                'ASSIGNED_TO': random.choice(self.sales_reps) if random.random() < 0.7 else None,
                'DUE_DATE': due_date,
                'RESOLUTION_DATE': resolution_date,
                'EFFECTIVE_START_DATE': effective_start,
                'EFFECTIVE_END_DATE': effective_end,
                'IS_PRIVATE': random.choice([True, False]),
                'TAGS': random.choice(['urgent, follow-up', 'customer, sales', 'support, technical', 'general, admin']),
                'CREATED_BY': random.choice(self.sales_reps),
                'CREATED_TIMESTAMP': created_date,
                'UPDATED_TIMESTAMP': created_date
            }
            
            notes.append(note)
            note_id_counter += 1
        
        df = pd.DataFrame(notes)
        
        # Convert date columns to proper SQL date strings
        if 'EFFECTIVE_START_DATE' in df.columns:
            df['EFFECTIVE_START_DATE'] = df['EFFECTIVE_START_DATE'].astype(str)
        if 'EFFECTIVE_END_DATE' in df.columns:
            df['EFFECTIVE_END_DATE'] = df['EFFECTIVE_END_DATE'].astype(str)
        if 'DUE_DATE' in df.columns:
            df['DUE_DATE'] = df['DUE_DATE'].astype(str)
        if 'RESOLUTION_DATE' in df.columns:
            df['RESOLUTION_DATE'] = df['RESOLUTION_DATE'].astype(str)
        if 'CREATED_TIMESTAMP' in df.columns:
            df['CREATED_TIMESTAMP'] = df['CREATED_TIMESTAMP'].astype(str)
        if 'UPDATED_TIMESTAMP' in df.columns:
            df['UPDATED_TIMESTAMP'] = df['UPDATED_TIMESTAMP'].astype(str)
        
        # Log note stats
        contact_notes = df['CONTACT_ID'].notna().sum()
        account_notes = df['ACCOUNT_ID'].notna().sum()
        general_notes = len(df) - contact_notes - account_notes
        logger.info(f"Generated {len(df):,} notes: {contact_notes:,} contact notes, {account_notes:,} account notes, {general_notes:,} general notes")
        
        return df
    
    def generate_campaigns(self, accounts_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
        """Generate realistic marketing campaigns"""
        logger.info(f"Generating sample campaigns...")
        
        campaigns = []
        campaign_id_counter = 1
        
        # Campaign types and categories
        campaign_types = ['Email', 'Social', 'Print', 'In-Store', 'Digital', 'Direct Mail']
        campaign_categories = ['Promotional', 'Seasonal', 'Product Launch', 'Brand Awareness', 'Customer Retention', 'Holiday']
        
        # Sample campaign names
        campaign_names = [
            'Summer Sale Blitz',
            'New Product Launch 2024',
            'Holiday Season Special',
            'Customer Appreciation Week',
            'Spring Refresh Campaign',
            'Back to School Sale',
            'Black Friday Extravaganza',
            'Cyber Monday Deals',
            'Valentine\'s Day Special',
            'Mother\'s Day Celebration',
            'Father\'s Day Offers',
            'End of Year Clearance',
            'Premium Customer Exclusive',
            'First-Time Buyer Welcome',
            'Loyalty Member Rewards'
        ]
        
        # Generate campaigns
        num_campaigns = max(8, len(accounts_df) // 4)  # Reasonable number of campaigns
        
        for i in range(num_campaigns):
            campaign_type = random.choice(campaign_types)
            campaign_category = random.choice(campaign_categories)
            
            # Generate campaign dates
            start_date = datetime.now() - timedelta(days=random.randint(30, 365))
            duration_days = random.randint(7, 90)  # 1 week to 3 months
            end_date = start_date + timedelta(days=duration_days)
            
            # Budget based on campaign type and category
            base_budget = {
                'Email': (1000, 5000),
                'Social': (2000, 8000),
                'Print': (3000, 12000),
                'In-Store': (5000, 20000),
                'Digital': (1500, 6000),
                'Direct Mail': (4000, 15000)
            }
            
            min_budget, max_budget = base_budget[campaign_type]
            budget = random.randint(min_budget, max_budget)
            
            # Actual spend (usually close to budget)
            actual_spend = budget * random.uniform(0.8, 1.1)
            
            # Target segment
            target_segment = random.choice(self.segments)
            
            # Target accounts (some campaigns target specific accounts, others all)
            if random.random() < 0.7:  # 70% target specific accounts
                num_target_accounts = random.randint(3, min(10, len(accounts_df)))
                target_accounts = ','.join(random.sample(accounts_df['ACCOUNT_ID'].tolist(), num_target_accounts))
            else:
                target_accounts = 'ALL'
            
            # Target products (some campaigns target specific products, others all)
            if random.random() < 0.6:  # 60% target specific products
                num_target_products = random.randint(2, min(8, len(products_df)))
                target_products = ','.join(random.sample(products_df['PRODUCT_ID'].tolist(), num_target_products))
            else:
                target_products = 'ALL'
            
            # Discount percentage
            discount_percentage = random.choice([0, 5, 10, 15, 20, 25, 30])
            
            # Status (most campaigns are active or completed)
            status_weights = {'Active': 0.3, 'Completed': 0.5, 'Paused': 0.1, 'Cancelled': 0.1}
            status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
            
            campaign = {
                'CAMPAIGN_ID': f'CAM{str(campaign_id_counter).zfill(4)}',
                'CAMPAIGN_NAME': campaign_names[i % len(campaign_names)],
                'CAMPAIGN_TYPE': campaign_type,
                'CAMPAIGN_CATEGORY': campaign_category,
                'DESCRIPTION': f'{campaign_category} campaign using {campaign_type.lower()} channels',
                'START_DATE': start_date.date(),
                'END_DATE': end_date.date(),
                'BUDGET': budget,
                'ACTUAL_SPEND': round(actual_spend, 2),
                'TARGET_SEGMENT': target_segment,
                'TARGET_ACCOUNTS': target_accounts,
                'TARGET_PRODUCTS': target_products,
                'DISCOUNT_PERCENTAGE': discount_percentage,
                'STATUS': status,
                'SUCCESS_METRICS': f'Campaign generated {random.randint(50, 500)} leads and {random.randint(10, 100)} conversions',
                'CREATED_BY': random.choice(self.sales_reps),
                'CREATED_TIMESTAMP': start_date - timedelta(days=random.randint(1, 30)),
                'UPDATED_TIMESTAMP': start_date - timedelta(days=random.randint(1, 30))
            }
            
            campaigns.append(campaign)
            campaign_id_counter += 1
        
        df = pd.DataFrame(campaigns)
        
        # Convert date columns to proper SQL date strings
        if 'START_DATE' in df.columns:
            df['START_DATE'] = df['START_DATE'].astype(str)
        if 'END_DATE' in df.columns:
            df['END_DATE'] = df['END_DATE'].astype(str)
        if 'CREATED_TIMESTAMP' in df.columns:
            df['CREATED_TIMESTAMP'] = df['CREATED_TIMESTAMP'].astype(str)
        if 'UPDATED_TIMESTAMP' in df.columns:
            df['UPDATED_TIMESTAMP'] = df['UPDATED_TIMESTAMP'].astype(str)
        
        # Log campaign stats
        active_campaigns = df[df['STATUS'] == 'Active'].shape[0]
        total_budget = df['BUDGET'].sum()
        logger.info(f"Generated {len(df):,} campaigns: {active_campaigns:,} active, Total Budget: ${total_budget:,.2f}")
        
        return df
    
    def load_data_to_snowflake(self) -> bool:
        """Generate and load all data to Snowflake"""
        logger.info("🚀 Starting comprehensive data generation and loading...")
        
        try:
            # Generate all data
            logger.info("📊 Generating accounts with hierarchy...")
            accounts_df = self.generate_accounts_with_hierarchy()
            
            logger.info("📦 Generating products...")
            products_df = self.generate_products()
            
            logger.info("👤 Generating contacts...")
            contacts_df = self.generate_contacts(accounts_df)
            
            logger.info("📝 Generating notes...")
            notes_df = self.generate_notes(accounts_df, contacts_df)
            
            logger.info("📢 Generating campaigns...")
            campaigns_df = self.generate_campaigns(accounts_df, products_df)
            
            logger.info("💰 Generating transactions...")
            transactions_df = self.generate_transactions(accounts_df, products_df, contacts_df, campaigns_df)
            
            logger.info("👥 Generating loyalty members...")
            loyalty_df = self.generate_loyalty_members(accounts_df, contacts_df)
            
            # Load to Snowflake in order (respecting foreign keys)
            logger.info("⬆️ Loading accounts to Snowflake...")
            success = self._load_dataframe_to_table(accounts_df, 'ACCOUNTS')
            if not success:
                return False
            
            logger.info("⬆️ Loading contacts to Snowflake...")
            success = self._load_dataframe_to_table(contacts_df, 'CONTACTS')
            if not success:
                return False
            
            logger.info("⬆️ Loading notes to Snowflake...")
            success = self._load_dataframe_to_table(notes_df, 'NOTES')
            if not success:
                return False
            
            logger.info("⬆️ Loading campaigns to Snowflake...")
            success = self._load_dataframe_to_table(campaigns_df, 'CAMPAIGNS')
            if not success:
                return False
            
            logger.info("⬆️ Loading products to Snowflake...")
            success = self._load_dataframe_to_table(products_df, 'PRODUCTS')
            if not success:
                return False
            
            logger.info("⬆️ Loading transactions to Snowflake...")
            success = self._load_dataframe_to_table(transactions_df, 'TRANSACTIONS')
            if not success:
                return False
            
            logger.info("⬆️ Loading loyalty members to Snowflake...")
            success = self._load_dataframe_to_table(loyalty_df, 'LOYALTY_MEMBERS')
            if not success:
                return False
            
            logger.info("✅ All data loaded successfully!")
            
            # Generate summary
            self._print_data_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Data generation/loading failed: {str(e)}")
            return False
    
    def _load_dataframe_to_table(self, df: pd.DataFrame, table_name: str) -> bool:
        """Helper to load DataFrame to Snowflake table"""
        try:
            # Clear existing data if any
            self.sf.execute_sql(f"DELETE FROM {table_name}")
            
            # Load data in batches
            batch_size = 1000
            total_rows = len(df)
            
            for i in range(0, total_rows, batch_size):
                batch_df = df.iloc[i:i + batch_size]
                
                # Convert DataFrame to INSERT statements
                for _, row in batch_df.iterrows():
                    # Prepare values, handling None/NaN
                    values = []
                    for val in row.values:
                        if pd.isna(val) or val is None or str(val) == 'None':
                            values.append('NULL')
                        elif isinstance(val, str):
                            # Escape single quotes in strings
                            escaped_val = val.replace("'", "''")
                            values.append(f"'{escaped_val}'")
                        elif hasattr(val, 'date'):  # Handle date objects
                            values.append(f"TO_DATE('{val}', 'YYYY-MM-DD')")
                        elif isinstance(val, str) and len(val) == 10 and val.count('-') == 2:  # Handle date strings (YYYY-MM-DD)
                            values.append(f"TO_DATE('{val}', 'YYYY-MM-DD')")
                        elif isinstance(val, bool):  # Handle boolean values
                            values.append(str(val).upper())
                        else:
                            values.append(str(val))
                    
                    columns = ', '.join(row.index.tolist())
                    values_str = ', '.join(values)
                    
                    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values_str})"
                    
                    if not self.sf.execute_sql(sql):
                        logger.error(f"Failed to insert row into {table_name}")
                        return False
            
            logger.info(f"✅ Loaded {total_rows:,} rows into {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load data to {table_name}: {str(e)}")
            return False
    
    def _print_data_summary(self):
        """Print summary of generated data"""
        try:
            summary_query = """
            SELECT 'ACCOUNTS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM ACCOUNTS
            UNION ALL
            SELECT 'CONTACTS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM CONTACTS
            UNION ALL
            SELECT 'NOTES' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM NOTES
            UNION ALL
            SELECT 'PRODUCTS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM PRODUCTS
            UNION ALL
            SELECT 'CAMPAIGNS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM CAMPAIGNS
            UNION ALL
            SELECT 'TRANSACTIONS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM TRANSACTIONS
            UNION ALL
            SELECT 'LOYALTY_MEMBERS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM LOYALTY_MEMBERS
            """
            
            result = self.sf.execute_query(summary_query)
            
            if result is not None:
                logger.info("\n📊 Data Summary:")
                for _, row in result.iterrows():
                    logger.info(f"• {row['TABLE_NAME']}: {row['ROW_COUNT']:,} rows")
            else:
                logger.warning("Could not retrieve data summary")
                
        except Exception as e:
            logger.error(f"Failed to print data summary: {str(e)}")