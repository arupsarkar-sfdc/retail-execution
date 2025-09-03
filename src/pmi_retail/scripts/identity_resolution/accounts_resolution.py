#!/usr/bin/env python3
"""
Advanced Account Identity Resolution with Levenshtein Distance
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
class AccountRecord:
    """Represents an account record from Snowflake ACCOUNTS table"""
    account_id: str
    account_name: str
    account_type: str
    parent_account_id: str
    segment: str
    address: str
    city: str
    state: str
    zip_code: str
    country: str
    phone: str
    email: str
    registration_date: str
    status: str
    hierarchy_level: int
    annual_revenue: float
    employee_count: int
    enterprise_id: str
    created_timestamp: str
    updated_timestamp: str

@dataclass
class AccountMatchResult:
    """Result of account identity resolution matching"""
    primary_account_id: str
    duplicate_account_ids: List[str]
    confidence_score: float
    match_reason: str
    detailed_match_reason: str
    match_type: str
    business_rules_applied: List[str]
    data_quality_score: float
    recommended_action: str
    total_revenue: float
    total_employees: int
    final_matches: List[Dict]  # Store the final matches for CSV generation
    unified_guid: str  # Unified GUID for the deduplicated group

class AccountIdentityResolutionEngine:
    """
    Advanced Account Identity Resolution Engine using Levenshtein Distance
    Implements proper fuzzy matching algorithms for accurate duplicate detection
    """
    
    def __init__(self, snowflake_manager: SnowflakeManager):
        self.sf = snowflake_manager
        self.fuzzy_matcher = FuzzyMatcher()
        
        # Business rules for different account segments
        self.business_rules = {
            'Enterprise': {
                'min_confidence': 0.30,
                'require_multiple_indicators': False,
                'manual_review_threshold': 0.50
            },
            'Mid-Market': {
                'min_confidence': 0.25,
                'require_multiple_indicators': False,
                'manual_review_threshold': 0.40
            },
            'SMB': {
                'min_confidence': 0.20,
                'require_multiple_indicators': False,
                'manual_review_threshold': 0.30
            }
        }
    
    def fetch_accounts_from_snowflake(self) -> List[AccountRecord]:
        """Fetch actual account data from Snowflake ACCOUNTS table"""
        logger.info("Fetching account data from Snowflake ACCOUNTS table...")
        
        try:
            query = """
            SELECT 
                ACCOUNT_ID,
                ACCOUNT_NAME,
                ACCOUNT_TYPE,
                PARENT_ACCOUNT_ID,
                SEGMENT,
                ADDRESS,
                CITY,
                STATE,
                ZIP_CODE,
                COUNTRY,
                PHONE,
                EMAIL,
                REGISTRATION_DATE,
                STATUS,
                HIERARCHY_LEVEL,
                ANNUAL_REVENUE,
                EMPLOYEE_COUNT,
                ENTERPRISE_ID,
                CREATED_TIMESTAMP,
                UPDATED_TIMESTAMP
            FROM ACCOUNTS
            ORDER BY ACCOUNT_ID
            """
            
            result = self.sf.execute_query(query)
            
            if result is None or result.empty:
                logger.warning("No data returned from ACCOUNTS table")
                return []
            
            accounts = []
            for _, row in result.iterrows():
                account = AccountRecord(
                    account_id=str(row.iloc[0]),
                    account_name=str(row.iloc[1]) if row.iloc[1] else '',
                    account_type=str(row.iloc[2]) if row.iloc[2] else '',
                    parent_account_id=str(row.iloc[3]) if row.iloc[3] else '',
                    segment=str(row.iloc[4]) if row.iloc[4] else 'SMB',
                    address=str(row.iloc[5]) if row.iloc[5] else '',
                    city=str(row.iloc[6]) if row.iloc[6] else '',
                    state=str(row.iloc[7]) if row.iloc[7] else '',
                    zip_code=str(row.iloc[8]) if row.iloc[8] else '',
                    country=str(row.iloc[9]) if row.iloc[9] else '',
                    phone=str(row.iloc[10]) if row.iloc[10] else '',
                    email=str(row.iloc[11]) if row.iloc[11] else '',
                    registration_date=str(row.iloc[12]) if row.iloc[12] else '',
                    status=str(row.iloc[13]) if row.iloc[13] else '',
                    hierarchy_level=int(row.iloc[14]) if row.iloc[14] else 1,
                    annual_revenue=float(row.iloc[15]) if row.iloc[15] else 0.0,
                    employee_count=int(row.iloc[16]) if row.iloc[16] else 0,
                    enterprise_id=str(row.iloc[17]) if row.iloc[17] else '',
                    created_timestamp=str(row.iloc[18]) if row.iloc[18] else '',
                    updated_timestamp=str(row.iloc[19]) if row.iloc[19] else ''
                )
                accounts.append(account)
            
            logger.info(f"Successfully fetched {len(accounts)} accounts from Snowflake")
            return accounts
            
        except Exception as e:
            logger.error(f"Error fetching accounts from Snowflake: {e}")
            return []
    
    def apply_business_rules(self, account: AccountRecord, matches: List[Dict]) -> Dict:
        """Apply business rules based on account segment"""
        # Determine segment based on revenue and employee count
        if account.annual_revenue >= 10000000 or account.employee_count >= 1000:
            segment = 'Enterprise'
        elif account.annual_revenue >= 1000000 or account.employee_count >= 100:
            segment = 'Mid-Market'
        else:
            segment = 'SMB'
        
        segment_rules = self.business_rules.get(segment, self.business_rules['SMB'])
        
        # Calculate data quality score
        data_quality_score = self.calculate_data_quality_score(account)
        
        # Determine if multiple indicators are required
        multiple_indicators = len([m for m in matches if m['weighted_score'] > 0.7]) >= 2
        
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
        elif max([m['weighted_score'] for m in matches]) >= manual_review_threshold:
            recommended_action = "High Confidence - Auto-Merge"
        elif max([m['weighted_score'] for m in matches]) >= min_confidence:
            recommended_action = "Manual Review Required"
        else:
            recommended_action = "No Action - Below Threshold"
        
        return {
            'segment': segment,
            'data_quality_score': data_quality_score,
            'multiple_indicators': multiple_indicators,
            'min_confidence': min_confidence,
            'manual_review_threshold': manual_review_threshold,
            'recommended_action': recommended_action
        }
    
    def calculate_data_quality_score(self, account: AccountRecord) -> float:
        """Calculate data quality score for an account record"""
        score = 0.0
        total_fields = 0
        
        # Check required fields
        if account.account_name and account.account_name.strip():
            score += 1.0
        total_fields += 1
        
        if account.account_type and account.account_type.strip():
            score += 1.0
        total_fields += 1
        
        # Check contact fields
        if account.phone and len(account.phone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')) >= 10:
            score += 1.0
        total_fields += 1
        
        if account.email and '@' in account.email:
            score += 1.0
        total_fields += 1
        
        # Check address fields
        if account.address and account.address.strip():
            score += 0.5
        total_fields += 0.5
        
        if account.city and account.city.strip():
            score += 0.5
        total_fields += 0.5
        
        if account.state and account.state.strip():
            score += 0.5
        total_fields += 0.5
        
        if account.zip_code and account.zip_code.strip():
            score += 0.5
        total_fields += 0.5
        
        if account.annual_revenue > 0:
            score += 1.0
        total_fields += 1
        
        return score / total_fields if total_fields > 0 else 0.0
    
    def resolve_account_identity(self, accounts: List[AccountRecord]) -> List[AccountMatchResult]:
        """Main account identity resolution method using Levenshtein distance"""
        logger.info("Starting account identity resolution process with Levenshtein distance...")
        
        results = []
        processed_records = set()
        
        for i, primary_account in enumerate(accounts):
            if primary_account.account_id in processed_records:
                continue
            
            matches = []
            duplicate_ids = []
            
            # Find potential matches using ENTERPRISE_ID exact matching
            for j, candidate_account in enumerate(accounts):
                if i == j or candidate_account.account_id in processed_records:
                    continue
                
                # Use new ENTERPRISE_ID matching logic
                identity_score = self.fuzzy_matcher.calculate_account_identity_score(
                    {
                        'ENTERPRISE_ID': primary_account.enterprise_id,
                        'ACCOUNT_NAME': primary_account.account_name,
                        'PHONE': primary_account.phone,
                        'EMAIL': primary_account.email
                    },
                    {
                        'ENTERPRISE_ID': candidate_account.enterprise_id,
                        'ACCOUNT_NAME': candidate_account.account_name,
                        'PHONE': candidate_account.phone,
                        'EMAIL': candidate_account.email
                    }
                )
                
                # Store match details for reporting
                match_details = {
                    'candidate': candidate_account,
                    'weighted_score': identity_score,
                    'individual_scores': {
                        'enterprise_id_match': 1.0 if primary_account.enterprise_id == candidate_account.enterprise_id and primary_account.enterprise_id else 0.0,
                        'name_score': 0.0,  # Not used in new rules
                        'phone_score': 0.0,  # Not used in new rules
                        'email_score': 0.0,  # Not used in new rules
                        'address_score': 0.0,  # Not used in new rules
                        'city_score': 0.0  # Not used in new rules
                    }
                }
                
                # ENTERPRISE_ID exact match (score = 1.0)
                if identity_score >= 1.0:
                    matches.append(match_details)
                    logger.debug(f"ENTERPRISE_ID match found: {primary_account.account_name} vs {candidate_account.account_name}, ENTERPRISE_ID: {primary_account.enterprise_id}")
            
            # Sort matches by score
            matches.sort(key=lambda x: x['weighted_score'], reverse=True)
            
            # Apply business rules
            business_rules_result = self.apply_business_rules(primary_account, matches)
            
            # Determine final matches based on business rules
            final_matches = []
            for match_detail in matches:
                if match_detail['weighted_score'] >= business_rules_result['min_confidence']:
                    final_matches.append(match_detail)
                    duplicate_ids.append(match_detail['candidate'].account_id)
                    processed_records.add(match_detail['candidate'].account_id)
            
            if final_matches:
                # Calculate overall confidence
                confidence_scores = [m['weighted_score'] for m in final_matches]
                overall_confidence = sum(confidence_scores) / len(confidence_scores)
                
                # Determine match reason with detailed scoring
                match_reasons = []
                detailed_reasons = []
                
                for match_detail in final_matches:
                    score = match_detail['weighted_score']
                    individual_scores = match_detail['individual_scores']
                    
                    if score >= 0.9:
                        match_reasons.append("High confidence exact match")
                    elif score >= 0.8:
                        match_reasons.append("Strong probabilistic match")
                    elif score >= 0.7:
                        match_reasons.append("Moderate similarity match")
                    
                    # Add detailed scoring breakdown
                    score_breakdown = []
                    if individual_scores['name_score'] > 0.7:
                        score_breakdown.append(f"Name: {individual_scores['name_score']:.2f}")
                    if individual_scores['phone_score'] > 0.7:
                        score_breakdown.append(f"Phone: {individual_scores['phone_score']:.2f}")
                    if individual_scores['email_score'] > 0.7:
                        score_breakdown.append(f"Email: {individual_scores['email_score']:.2f}")
                    if individual_scores['address_score'] > 0.7:
                        score_breakdown.append(f"Address: {individual_scores['address_score']:.2f}")
                    if individual_scores['city_score'] > 0.7:
                        score_breakdown.append(f"City: {individual_scores['city_score']:.2f}")
                    
                    if score_breakdown:
                        detailed_reasons.append(f"Match {match_detail['candidate'].account_id}: {' + '.join(score_breakdown)}")
                
                match_reason = "; ".join(match_reasons)
                detailed_match_reason = " | ".join(detailed_reasons)
                
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
                business_rules_applied.append(f"Segment: {business_rules_result['segment']}")
                business_rules_applied.append(f"Segment threshold: {business_rules_result['min_confidence']}")
                business_rules_applied.append(f"Manual review threshold: {business_rules_result['manual_review_threshold']}")
                
                # Calculate aggregated metrics
                all_accounts = [primary_account] + [m['candidate'] for m in final_matches]
                total_revenue = sum(acc.annual_revenue for acc in all_accounts)
                total_employees = sum(acc.employee_count for acc in all_accounts)
                
                # Generate unified GUID for this deduplicated group
                unified_guid = str(uuid.uuid4())
                
                result = AccountMatchResult(
                    primary_account_id=primary_account.account_id,
                    duplicate_account_ids=duplicate_ids,
                    confidence_score=overall_confidence,
                    match_reason=match_reason,
                    detailed_match_reason=detailed_match_reason,
                    match_type=match_type,
                    business_rules_applied=business_rules_applied,
                    data_quality_score=business_rules_result['data_quality_score'],
                    recommended_action=business_rules_result['recommended_action'],
                    total_revenue=total_revenue,
                    total_employees=total_employees,
                    final_matches=final_matches,
                    unified_guid=unified_guid
                )
                
                results.append(result)
                processed_records.add(primary_account.account_id)
        
        logger.info(f"Account identity resolution completed. Found {len(results)} match groups.")
        return results
    
    def generate_output_csv(self, accounts: List[AccountRecord], results: List[AccountMatchResult]) -> str:
        """Generate output CSV with proper naming convention for ACCOUNTS"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ACCOUNTS_identity_resolution_{timestamp}.csv"
        
        # Create output data
        output_data = []
        
        for result in results:
            # Get primary account details
            primary_account = next(a for a in accounts if a.account_id == result.primary_account_id)
            
            # Get duplicate account details
            duplicate_accounts = [a for a in accounts if a.account_id in result.duplicate_account_ids]
            
            # Create row for primary account
            output_data.append({
                'ACCOUNT_ID': primary_account.account_id,
                'ACCOUNT_NAME': primary_account.account_name,
                'ACCOUNT_TYPE': primary_account.account_type,
                'SEGMENT': primary_account.segment,
                'PHONE': primary_account.phone or '',
                'EMAIL': primary_account.email or '',
                'ADDRESS': primary_account.address or '',
                'CITY': primary_account.city or '',
                'STATE': primary_account.state or '',
                'ZIP_CODE': primary_account.zip_code or '',
                'ANNUAL_REVENUE': primary_account.annual_revenue,
                'EMPLOYEE_COUNT': primary_account.employee_count,
                'HIERARCHY_LEVEL': primary_account.hierarchy_level,
                'MATCH_TYPE': 'PRIMARY',
                'DUPLICATE_GROUP_ID': f"GROUP_{primary_account.account_id}",
                'UNIFIED_GUID': result.unified_guid,
                'CONFIDENCE_SCORE': result.confidence_score,
                'MATCH_REASON': result.match_reason,
                'DETAILED_MATCH_REASON': result.detailed_match_reason,
                'FIELD_SCORES': 'N/A (Primary Record)',
                'BUSINESS_RULES_APPLIED': '; '.join(result.business_rules_applied),
                'DATA_QUALITY_SCORE': result.data_quality_score,
                'RECOMMENDED_ACTION': result.recommended_action,
                'TOTAL_GROUP_REVENUE': result.total_revenue,
                'TOTAL_GROUP_EMPLOYEES': result.total_employees,
                'PROCESSING_TIMESTAMP': timestamp
            })
            
            # Create rows for duplicate accounts with individual field scores
            for match_detail in result.final_matches:
                dup_account = match_detail['candidate']
                individual_scores = match_detail['individual_scores']
                
                # Format field scores for CSV
                field_scores = f"Name: {individual_scores['name_score']:.3f}, Phone: {individual_scores['phone_score']:.3f}, Email: {individual_scores['email_score']:.3f}, Address: {individual_scores['address_score']:.3f}, City: {individual_scores['city_score']:.3f}"
                
                output_data.append({
                    'ACCOUNT_ID': dup_account.account_id,
                    'ACCOUNT_NAME': dup_account.account_name,
                    'ACCOUNT_TYPE': dup_account.account_type,
                    'SEGMENT': dup_account.segment,
                    'PHONE': dup_account.phone or '',
                    'EMAIL': dup_account.email or '',
                    'ADDRESS': dup_account.address or '',
                    'CITY': dup_account.city or '',
                    'STATE': dup_account.state or '',
                    'ZIP_CODE': dup_account.zip_code or '',
                    'ANNUAL_REVENUE': dup_account.annual_revenue,
                    'EMPLOYEE_COUNT': dup_account.employee_count,
                    'HIERARCHY_LEVEL': dup_account.hierarchy_level,
                    'MATCH_TYPE': 'DUPLICATE',
                    'DUPLICATE_GROUP_ID': f"GROUP_{primary_account.account_id}",
                    'UNIFIED_GUID': result.unified_guid,
                    'CONFIDENCE_SCORE': result.confidence_score,
                    'MATCH_REASON': result.match_reason,
                    'DETAILED_MATCH_REASON': result.detailed_match_reason,
                    'FIELD_SCORES': field_scores,
                    'BUSINESS_RULES_APPLIED': '; '.join(result.business_rules_applied),
                    'DATA_QUALITY_SCORE': result.data_quality_score,
                    'RECOMMENDED_ACTION': result.recommended_action,
                    'TOTAL_GROUP_REVENUE': result.total_revenue,
                    'TOTAL_GROUP_EMPLOYEES': result.total_employees,
                    'PROCESSING_TIMESTAMP': timestamp
                })
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(output_data)
        df.to_csv(filename, index=False)
        
        logger.info(f"ACCOUNTS output CSV generated: {filename}")
        return filename

def main():
    """Main execution function for ACCOUNTS identity resolution"""
    logger.info("🚀 Starting ACCOUNTS Identity Resolution Job with Levenshtein Distance")
    logger.info("This demonstrates advanced fuzzy matching using proper Levenshtein distance algorithms")
    
    try:
        # Initialize Snowflake connection
        sf = SnowflakeManager()
        sf.connect()
        
        # Initialize the engine
        engine = AccountIdentityResolutionEngine(sf)
        
        # Fetch real account data from Snowflake
        accounts = engine.fetch_accounts_from_snowflake()
        
        if not accounts:
            logger.error("No accounts found in Snowflake. Exiting.")
            return
        
        # Run account identity resolution
        results = engine.resolve_account_identity(accounts)
        
        # Generate output CSV
        output_file = engine.generate_output_csv(accounts, results)
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("📊 ACCOUNTS IDENTITY RESOLUTION SUMMARY (Levenshtein Distance)")
        logger.info("="*80)
        
        total_records = len(accounts)
        matched_records = sum(len(r.duplicate_account_ids) + 1 for r in results)
        unique_accounts = len(results)
        
        logger.info(f"Total Accounts Processed: {total_records}")
        logger.info(f"Accounts with Matches: {matched_records}")
        logger.info(f"Unique Accounts Identified: {unique_accounts}")
        if total_records > 0:
            duplicate_reduction = ((total_records - unique_accounts) / total_records * 100)
            logger.info(f"Duplicate Reduction: {duplicate_reduction:.1f}%")
        
        # Show sample results
        if results:
            logger.info("\n🔍 SAMPLE MATCH RESULTS:")
            for i, result in enumerate(results[:3]):  # Show first 3
                logger.info(f"\nMatch Group {i+1}:")
                logger.info(f"  Primary: {result.primary_account_id}")
                logger.info(f"  Duplicates: {', '.join(result.duplicate_account_ids)}")
                logger.info(f"  Confidence: {result.confidence_score:.2f}")
                logger.info(f"  Reason: {result.match_reason}")
                logger.info(f"  Action: {result.recommended_action}")
                logger.info(f"  Total Revenue: ${result.total_revenue:,.2f}")
                logger.info(f"  Total Employees: {result.total_employees}")
        
        logger.info(f"\n📁 Output saved to: {output_file}")
        logger.info("\n✅ ACCOUNTS Identity Resolution Job completed successfully!")
        
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
