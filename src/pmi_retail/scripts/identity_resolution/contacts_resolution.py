#!/usr/bin/env python3
"""
Advanced Contact Identity Resolution with Levenshtein Distance
Uses proper fuzzy matching algorithms for accurate duplicate detection
"""

import pandas as pd
import numpy as np
from datetime import datetime
import uuid
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path
from dataclasses import dataclass

# Import our existing Snowflake connection
try:
    from pmi_retail.database.snowflake.connection import SnowflakeManager
    from pmi_retail.config import settings
    from pmi_retail.scripts.identity_resolution.utils.fuzzy_matching import FuzzyMatcher
except ImportError as e:
    print(f"Error: Cannot import required modules: {e}")
    print("Make sure you're running from the project root and dependencies are installed.")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ContactRecord:
    """Represents a contact record from Snowflake CONTACTS table"""
    contact_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    mobile_phone: str
    contact_type: str
    account_id: str
    job_title: str
    department: str
    address_line1: str
    city: str
    state: str
    zip_code: str
    status: str
    created_timestamp: str
    updated_timestamp: str

@dataclass
class ContactMatchResult:
    """Result of contact identity resolution matching"""
    primary_contact_id: str
    duplicate_contact_ids: List[str]
    confidence_score: float
    match_reason: str
    match_type: str
    business_rules_applied: List[str]
    data_quality_score: float
    recommended_action: str
    total_contacts_in_group: int
    linked_accounts: List[str]
    unified_guid: str  # Unified GUID for the deduplicated group

class ContactIdentityResolutionEngine:
    """Advanced Contact Identity Resolution Engine using Levenshtein Distance"""
    
    def __init__(self, snowflake_manager: SnowflakeManager):
        self.sf = snowflake_manager
        self.fuzzy_matcher = FuzzyMatcher()
        
        # Business rules for different contact types
        self.business_rules = {
            'Consumer': {
                'min_confidence': 0.20,
                'require_multiple_indicators': False,
                'manual_review_threshold': 0.30
            },
            'Business': {
                'min_confidence': 0.25,
                'require_multiple_indicators': False,
                'manual_review_threshold': 0.35
            },
            'Partner': {
                'min_confidence': 0.20,
                'require_multiple_indicators': False,
                'manual_review_threshold': 0.30
            }
        }
    
    def fetch_contacts_from_snowflake(self) -> List[ContactRecord]:
        """Fetch actual contact data from Snowflake CONTACTS table"""
        logger.info("Fetching contact data from Snowflake CONTACTS table...")
        
        try:
            query = """
            SELECT 
                CONTACT_ID,
                FIRST_NAME,
                LAST_NAME,
                EMAIL,
                PHONE,
                MOBILE_PHONE,
                CONTACT_TYPE,
                ACCOUNT_ID,
                JOB_TITLE,
                DEPARTMENT,
                ADDRESS_LINE1,
                CITY,
                STATE,
                ZIP_CODE,
                STATUS,
                CREATED_TIMESTAMP,
                UPDATED_TIMESTAMP
            FROM CONTACTS
            ORDER BY CONTACT_ID
            """
            
            result = self.sf.execute_query(query)
            
            if result is None or result.empty:
                logger.warning("No data returned from CONTACTS table")
                return []
            
            contacts = []
            for _, row in result.iterrows():
                contact = ContactRecord(
                    contact_id=str(row.iloc[0]),
                    first_name=str(row.iloc[1]) if row.iloc[1] else '',
                    last_name=str(row.iloc[2]) if row.iloc[2] else '',
                    email=str(row.iloc[3]) if row.iloc[3] else '',
                    phone=str(row.iloc[4]) if row.iloc[4] else '',
                    mobile_phone=str(row.iloc[5]) if row.iloc[5] else '',
                    contact_type=str(row.iloc[6]) if row.iloc[6] else 'Consumer',
                    account_id=str(row.iloc[7]) if row.iloc[7] else '',
                    job_title=str(row.iloc[8]) if row.iloc[8] else '',
                    department=str(row.iloc[9]) if row.iloc[9] else '',
                    address_line1=str(row.iloc[10]) if row.iloc[10] else '',
                    city=str(row.iloc[11]) if row.iloc[11] else '',
                    state=str(row.iloc[12]) if row.iloc[12] else '',
                    zip_code=str(row.iloc[13]) if row.iloc[13] else '',
                    status=str(row.iloc[14]) if row.iloc[14] else 'Active',
                    created_timestamp=str(row.iloc[15]) if row.iloc[15] else '',
                    updated_timestamp=str(row.iloc[16]) if row.iloc[16] else ''
                )
                contacts.append(contact)
            
            logger.info(f"Successfully fetched {len(contacts)} contacts from Snowflake")
            return contacts
            
        except Exception as e:
            logger.error(f"Error fetching contacts from Snowflake: {e}")
            return []
    
    def apply_business_rules(self, contact: ContactRecord, matches: List[Tuple[ContactRecord, float]]) -> Dict:
        """Apply business rules based on contact type"""
        contact_type = contact.contact_type or 'Consumer'
        segment_rules = self.business_rules.get(contact_type, self.business_rules['Consumer'])
        
        # Calculate data quality score
        data_quality_score = self.calculate_data_quality_score(contact)
        
        # Determine if multiple indicators are required
        multiple_indicators = len([m for m in matches if m[1] > 0.7]) >= 2
        
        # Apply confidence thresholds
        min_confidence = segment_rules['min_confidence']
        manual_review_threshold = segment_rules['manual_review_threshold']
        
        # Determine recommended action
        if not matches:
            recommended_action = "No Matches Found"
        elif data_quality_score < 0.6:
            recommended_action = "Data Quality Review Required"
        elif multiple_indicators and segment_rules['require_multiple_indicators']:
            recommended_action = "Multiple Indicators Verified - Auto-Merge"
        elif max([m[1] for m in matches]) >= manual_review_threshold:
            recommended_action = "High Confidence - Auto-Merge"
        elif max([m[1] for m in matches]) >= min_confidence:
            recommended_action = "Manual Review Required"
        else:
            recommended_action = "No Action - Below Threshold"
        
        return {
            'contact_type': contact_type,
            'data_quality_score': data_quality_score,
            'multiple_indicators': multiple_indicators,
            'min_confidence': min_confidence,
            'manual_review_threshold': manual_review_threshold,
            'recommended_action': recommended_action
        }
    
    def calculate_data_quality_score(self, contact: ContactRecord) -> float:
        """Calculate data quality score for a contact record"""
        score = 0.0
        total_fields = 0
        
        # Check required fields
        if contact.first_name and contact.first_name.strip():
            score += 1.0
        total_fields += 1
        
        if contact.last_name and contact.last_name.strip():
            score += 1.0
        total_fields += 1
        
        # Check contact fields
        if contact.email and '@' in contact.email:
            score += 1.0
        total_fields += 1
        
        if contact.phone and len(contact.phone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')) >= 10:
            score += 1.0
        total_fields += 1
        
        # Check business fields
        if contact.job_title and contact.job_title.strip():
            score += 1.0
        total_fields += 1
        
        if contact.department and contact.department.strip():
            score += 0.5
        total_fields += 0.5
        
        return score / total_fields if total_fields > 0 else 0.0
    
    def resolve_contact_identity(self, contacts: List[ContactRecord]) -> List[ContactMatchResult]:
        """Main contact identity resolution method using Levenshtein distance"""
        logger.info("Starting contact identity resolution process with Levenshtein distance...")
        
        results = []
        processed_records = set()
        
        for i, primary_contact in enumerate(contacts):
            if primary_contact.contact_id in processed_records:
                continue
            
            matches = []
            duplicate_ids = []
            
            # Find potential matches using new specific identity resolution rules
            for j, candidate_contact in enumerate(contacts):
                if i == j or candidate_contact.contact_id in processed_records:
                    continue
                
                # Use new specific identity resolution rules
                identity_score = self.fuzzy_matcher.calculate_contact_identity_score(
                    {
                        'FIRST_NAME': primary_contact.first_name,
                        'LAST_NAME': primary_contact.last_name,
                        'EMAIL': primary_contact.email,
                        'PHONE': primary_contact.phone
                    },
                    {
                        'FIRST_NAME': candidate_contact.first_name,
                        'LAST_NAME': candidate_contact.last_name,
                        'EMAIL': candidate_contact.email,
                        'PHONE': candidate_contact.phone
                    }
                )
                
                # Apply business rules - Only exact matches (score = 0.95) for new rules
                if identity_score >= 0.95:  # Exact match based on new rules
                    matches.append((candidate_contact, identity_score))
                    logger.debug(f"Identity match found: {primary_contact.first_name} {primary_contact.last_name} vs {candidate_contact.first_name} {candidate_contact.last_name}, Score: {identity_score:.3f}")
                    logger.debug(f"  Rules: First Name fuzzy={self.fuzzy_matcher.calculate_first_name_similarity(primary_contact.first_name, candidate_contact.first_name):.3f}, Last Name exact={1.0 if primary_contact.last_name.lower() == candidate_contact.last_name.lower() else 0.0}, Email exact={1.0 if primary_contact.email.lower() == candidate_contact.email.lower() else 0.0}, Phone digits={1.0 if ''.join(filter(str.isdigit, primary_contact.phone)) == ''.join(filter(str.isdigit, candidate_contact.phone)) else 0.0}")
            
            # Sort matches by score
            matches.sort(key=lambda x: x[1], reverse=True)
            
            # Apply business rules
            business_rules_result = self.apply_business_rules(primary_contact, matches)
            
            # Determine final matches based on business rules
            final_matches = []
            for contact, score in matches:
                if score >= business_rules_result['min_confidence']:
                    final_matches.append((contact, score))
                    duplicate_ids.append(contact.contact_id)
                    processed_records.add(contact.contact_id)
            
            if final_matches:
                # Calculate overall confidence
                confidence_scores = [m[1] for m in final_matches]
                overall_confidence = sum(confidence_scores) / len(confidence_scores)
                
                # Determine match reason
                match_reasons = []
                if any(m[1] >= 0.9 for m in final_matches):
                    match_reasons.append("High confidence exact match")
                if any(m[1] >= 0.8 for m in final_matches):
                    match_reasons.append("Strong probabilistic match")
                if any(m[1] >= 0.7 for m in final_matches):
                    match_reasons.append("Moderate similarity match")
                
                match_reason = "; ".join(match_reasons)
                
                # Determine match type
                if overall_confidence >= 0.9:
                    match_type = "Exact Match"
                elif overall_confidence >= 0.8:
                    match_type = "Probabilistic Match"
                else:
                    match_type = "Fuzzy Match"
                
                # Business rules applied
                business_rules_applied = []
                if business_rules_result['multiple_indicators']:
                    business_rules_applied.append("Multiple indicators required")
                business_rules_applied.append(f"Contact type: {business_rules_result['contact_type']}")
                business_rules_applied.append(f"Type threshold: {business_rules_result['min_confidence']}")
                business_rules_applied.append(f"Manual review threshold: {business_rules_result['manual_review_threshold']}")
                
                # Calculate aggregated metrics
                all_contacts = [primary_contact] + [m[0] for m in final_matches]
                total_contacts = len(all_contacts)
                linked_accounts = list(set([c.account_id for c in all_contacts if c.account_id]))
                
                # Generate unified GUID for this deduplicated group
                unified_guid = str(uuid.uuid4())
                
                result = ContactMatchResult(
                    primary_contact_id=primary_contact.contact_id,
                    duplicate_contact_ids=duplicate_ids,
                    confidence_score=overall_confidence,
                    match_reason=match_reason,
                    match_type=match_type,
                    business_rules_applied=business_rules_applied,
                    data_quality_score=business_rules_result['data_quality_score'],
                    recommended_action=business_rules_result['recommended_action'],
                    total_contacts_in_group=total_contacts,
                    linked_accounts=linked_accounts,
                    unified_guid=unified_guid
                )
                
                results.append(result)
                processed_records.add(primary_contact.contact_id)
        
        logger.info(f"Contact identity resolution completed. Found {len(results)} match groups.")
        return results
    
    def generate_output_csv(self, contacts: List[ContactRecord], results: List[ContactMatchResult]) -> str:
        """Generate output CSV with proper naming convention for CONTACTS"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"CONTACTS_identity_resolution_{timestamp}.csv"
        
        # Create output data
        output_data = []
        
        for result in results:
            # Get primary contact details
            primary_contact = next(c for c in contacts if c.contact_id == result.primary_contact_id)
            
            # Get duplicate contact details
            duplicate_contacts = [c for c in contacts if c.contact_id in result.duplicate_contact_ids]
            
            # Create row for primary contact
            output_data.append({
                'CONTACT_ID': primary_contact.contact_id,
                'FIRST_NAME': primary_contact.first_name,
                'LAST_NAME': primary_contact.last_name,
                'EMAIL': primary_contact.email or '',
                'PHONE': primary_contact.phone or '',
                'MOBILE_PHONE': primary_contact.mobile_phone or '',
                'CONTACT_TYPE': primary_contact.contact_type,
                'ACCOUNT_ID': primary_contact.account_id or '',
                'JOB_TITLE': primary_contact.job_title or '',
                'DEPARTMENT': primary_contact.department or '',
                'ADDRESS_LINE1': primary_contact.address_line1 or '',
                'CITY': primary_contact.city or '',
                'STATE': primary_contact.state or '',
                'ZIP_CODE': primary_contact.zip_code or '',
                'STATUS': primary_contact.status,
                'MATCH_TYPE': 'PRIMARY',
                'DUPLICATE_GROUP_ID': f"GROUP_{primary_contact.contact_id}",
                'UNIFIED_GUID': result.unified_guid,
                'CONFIDENCE_SCORE': result.confidence_score,
                'MATCH_REASON': result.match_reason,
                'BUSINESS_RULES_APPLIED': '; '.join(result.business_rules_applied),
                'DATA_QUALITY_SCORE': result.data_quality_score,
                'RECOMMENDED_ACTION': result.recommended_action,
                'TOTAL_CONTACTS_IN_GROUP': result.total_contacts_in_group,
                'LINKED_ACCOUNTS': '; '.join(result.linked_accounts),
                'PROCESSING_TIMESTAMP': timestamp
            })
            
            # Create rows for duplicate contacts
            for dup_contact in duplicate_contacts:
                output_data.append({
                    'CONTACT_ID': dup_contact.contact_id,
                    'FIRST_NAME': dup_contact.first_name,
                    'LAST_NAME': dup_contact.last_name,
                    'EMAIL': dup_contact.email or '',
                    'PHONE': dup_contact.phone or '',
                    'MOBILE_PHONE': dup_contact.mobile_phone or '',
                    'CONTACT_TYPE': dup_contact.contact_type,
                    'ACCOUNT_ID': dup_contact.account_id or '',
                    'JOB_TITLE': dup_contact.job_title or '',
                    'DEPARTMENT': dup_contact.department or '',
                    'ADDRESS_LINE1': dup_contact.address_line1 or '',
                    'CITY': dup_contact.city or '',
                    'STATE': dup_contact.state or '',
                    'ZIP_CODE': dup_contact.zip_code or '',
                    'STATUS': dup_contact.status,
                    'MATCH_TYPE': 'DUPLICATE',
                    'DUPLICATE_GROUP_ID': f"GROUP_{primary_contact.contact_id}",
                    'UNIFIED_GUID': result.unified_guid,
                    'CONFIDENCE_SCORE': result.confidence_score,
                    'MATCH_REASON': result.match_reason,
                    'BUSINESS_RULES_APPLIED': '; '.join(result.business_rules_applied),
                    'DATA_QUALITY_SCORE': result.data_quality_score,
                    'RECOMMENDED_ACTION': result.recommended_action,
                    'TOTAL_CONTACTS_IN_GROUP': result.total_contacts_in_group,
                    'LINKED_ACCOUNTS': '; '.join(result.linked_accounts),
                    'PROCESSING_TIMESTAMP': timestamp
                })
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(output_data)
        df.to_csv(filename, index=False)
        
        logger.info(f"CONTACTS output CSV generated: {filename}")
        return filename

def main():
    """Main execution function for CONTACTS identity resolution"""
    logger.info("🚀 Starting CONTACTS Identity Resolution Job with Levenshtein Distance")
    logger.info("This demonstrates advanced fuzzy matching using proper Levenshtein distance algorithms")
    
    try:
        # Initialize Snowflake connection
        sf = SnowflakeManager()
        sf.connect()
        
        # Initialize the engine
        engine = ContactIdentityResolutionEngine(sf)
        
        # Fetch real contact data from Snowflake
        contacts = engine.fetch_contacts_from_snowflake()
        
        if not contacts:
            logger.error("No contacts found in Snowflake. Exiting.")
            return
        
        # Run contact identity resolution
        results = engine.resolve_contact_identity(contacts)
        
        # Generate output CSV
        output_file = engine.generate_output_csv(contacts, results)
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("📊 CONTACTS IDENTITY RESOLUTION SUMMARY (Levenshtein Distance)")
        logger.info("="*80)
        
        total_records = len(contacts)
        matched_records = sum(len(r.duplicate_contact_ids) + 1 for r in results)
        unique_contacts = len(results)
        
        logger.info(f"Total Contacts Processed: {total_records}")
        logger.info(f"Contacts with Matches: {matched_records}")
        logger.info(f"Unique Contacts Identified: {unique_contacts}")
        if total_records > 0:
            duplicate_reduction = ((total_records - unique_contacts) / total_records * 100)
            logger.info(f"Duplicate Reduction: {duplicate_reduction:.1f}%")
        
        # Show sample results
        if results:
            logger.info("\n🔍 SAMPLE MATCH RESULTS:")
            for i, result in enumerate(results[:3]):  # Show first 3
                logger.info(f"\nMatch Group {i+1}:")
                logger.info(f"  Primary: {result.primary_contact_id}")
                logger.info(f"  Duplicates: {', '.join(result.duplicate_contact_ids)}")
                logger.info(f"  Confidence: {result.confidence_score:.2f}")
                logger.info(f"  Reason: {result.match_reason}")
                logger.info(f"  Action: {result.recommended_action}")
                logger.info(f"  Total Contacts: {result.total_contacts_in_group}")
                logger.info(f"  Linked Accounts: {', '.join(result.linked_accounts) if result.linked_accounts else 'None'}")
        
        logger.info(f"\n📁 Output saved to: {output_file}")
        logger.info("\n✅ CONTACTS Identity Resolution Job completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise
    finally:
        # Close Snowflake connection
        try:
            sf.close()
        except:
            pass

if __name__ == "__main__":
    main()
