"""
Advanced Fuzzy Matching Utilities using Levenshtein Distance
Implements proper fuzzy string matching algorithms for identity resolution
"""

import re
from typing import Tuple, Dict, List
from fuzzywuzzy import fuzz, process
from fuzzywuzzy.utils import full_process


class FuzzyMatcher:
    """
    Advanced fuzzy matching class using Levenshtein distance algorithms
    Provides multiple similarity scoring methods for identity resolution
    """
    
    def __init__(self):
        # Business abbreviation mappings
        self.business_abbreviations = {
            'corporation': 'corp',
            'incorporated': 'inc',
            'limited': 'ltd',
            'company': 'co',
            'and': '&',
            'plus': '+',
            'street': 'st',
            'avenue': 'ave',
            'boulevard': 'blvd',
            'drive': 'dr',
            'road': 'rd',
            'suite': 'ste',
            'floor': 'fl'
        }
        
        # City abbreviation mappings
        self.city_abbreviations = {
            'new york': 'nyc',
            'los angeles': 'la',
            'san francisco': 'sf',
            'washington dc': 'dc',
            'chicago': 'chi'
        }
    
    def normalize_string(self, text: str) -> str:
        """Normalize string for better matching"""
        if not text:
            return ""
        
        # Convert to lowercase and strip
        text = text.lower().strip()
        
        # Remove special characters except spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def apply_abbreviations(self, text: str, abbreviation_map: Dict[str, str]) -> str:
        """Apply abbreviation mappings to text"""
        words = text.split()
        normalized_words = []
        
        for word in words:
            # Check if word is in abbreviation map
            if word in abbreviation_map:
                normalized_words.append(abbreviation_map[word])
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names using multiple Levenshtein distance methods
        Returns a score between 0.0 and 1.0
        """
        if not name1 or not name2:
            return 0.0
        
        # Normalize names
        norm_name1 = self.normalize_string(name1)
        norm_name2 = self.normalize_string(name2)
        
        # Exact match after normalization
        if norm_name1 == norm_name2:
            return 1.0
        
        # Apply business abbreviations
        norm_name1 = self.apply_abbreviations(norm_name1, self.business_abbreviations)
        norm_name2 = self.apply_abbreviations(norm_name2, self.business_abbreviations)
        
        # Check exact match after abbreviation normalization
        if norm_name1 == norm_name2:
            return 0.95
        
        # Calculate multiple similarity scores using Levenshtein distance
        scores = []
        
        # 1. Simple Ratio (basic Levenshtein distance)
        simple_ratio = fuzz.ratio(norm_name1, norm_name2) / 100.0
        scores.append(simple_ratio)
        
        # 2. Partial Ratio (best substring match)
        partial_ratio = fuzz.partial_ratio(norm_name1, norm_name2) / 100.0
        scores.append(partial_ratio)
        
        # 3. Token Sort Ratio (ignores word order)
        token_sort_ratio = fuzz.token_sort_ratio(norm_name1, norm_name2) / 100.0
        scores.append(token_sort_ratio)
        
        # 4. Token Set Ratio (ignores duplicates and order)
        token_set_ratio = fuzz.token_set_ratio(norm_name1, norm_name2) / 100.0
        scores.append(token_set_ratio)
        
        # 5. Weighted Average (emphasize token-based matching for names)
        weighted_score = (
            simple_ratio * 0.2 +
            partial_ratio * 0.2 +
            token_sort_ratio * 0.3 +
            token_set_ratio * 0.3
        )
        scores.append(weighted_score)
        
        # Return the maximum score (best match)
        return max(scores)
    
    def calculate_contact_name_similarity(self, first1: str, last1: str, first2: str, last2: str) -> float:
        """
        Calculate similarity between two contact names (first + last)
        Uses Levenshtein distance for individual name components
        """
        if not all([first1, last1, first2, last2]):
            return 0.0
        
        # Normalize individual names
        norm_first1 = self.normalize_string(first1)
        norm_first2 = self.normalize_string(first2)
        norm_last1 = self.normalize_string(last1)
        norm_last2 = self.normalize_string(last2)
        
        # Calculate first name similarity
        first_scores = []
        first_scores.append(fuzz.ratio(norm_first1, norm_first2) / 100.0)
        first_scores.append(fuzz.partial_ratio(norm_first1, norm_first2) / 100.0)
        
        # Handle abbreviations (J. vs John)
        if (len(norm_first1) == 1 and norm_first2.startswith(norm_first1)) or \
           (len(norm_first2) == 1 and norm_first1.startswith(norm_first2)):
            first_scores.append(0.9)
        
        first_similarity = max(first_scores)
        
        # Calculate last name similarity
        last_scores = []
        last_scores.append(fuzz.ratio(norm_last1, norm_last2) / 100.0)
        last_scores.append(fuzz.partial_ratio(norm_last1, norm_last2) / 100.0)
        
        # Handle abbreviations for last names
        if (len(norm_last1) == 1 and norm_last2.startswith(norm_last1)) or \
           (len(norm_last2) == 1 and norm_last1.startswith(norm_last2)):
            last_scores.append(0.9)
        
        last_similarity = max(last_scores)
        
        # Weight first and last names equally
        return (first_similarity + last_similarity) / 2.0
    
    def calculate_phone_similarity(self, phone1: str, phone2: str) -> float:
        """
        Calculate similarity between two phone numbers using Levenshtein distance
        Handles various phone number formats and extensions
        """
        if not phone1 or not phone2:
            return 0.0
        
        # Normalize phone numbers (digits only)
        digits1 = re.sub(r'[^\d]', '', phone1)
        digits2 = re.sub(r'[^\d]', '', phone2)
        
        # Exact match
        if digits1 == digits2:
            return 1.0
        
        # Handle extensions (one number contains the other)
        if digits1 in digits2 or digits2 in digits1:
            return 0.9
        
        # For US numbers, compare last 10 digits
        if len(digits1) >= 10 and len(digits2) >= 10:
            last1 = digits1[-10:]
            last2 = digits2[-10:]
            if last1 == last2:
                return 0.95
            
            # Use Levenshtein distance for partial matches
            similarity = fuzz.ratio(last1, last2) / 100.0
            if similarity > 0.8:  # High similarity threshold for phone numbers
                return similarity * 0.8  # Scale down for partial matches
        
        # General Levenshtein distance for other cases
        return fuzz.ratio(digits1, digits2) / 100.0
    
    def calculate_email_similarity(self, email1: str, email2: str) -> float:
        """
        Calculate similarity between two email addresses
        Uses Levenshtein distance with domain/local part weighting
        """
        if not email1 or not email2:
            return 0.0
        
        # Exact match (case insensitive)
        if email1.lower() == email2.lower():
            return 1.0
        
        try:
            # Split into local and domain parts
            local1, domain1 = email1.lower().split('@')
            local2, domain2 = email2.lower().split('@')
            
            # Domain similarity (more important - 60% weight)
            domain_similarity = fuzz.ratio(domain1, domain2) / 100.0
            
            # Local part similarity (40% weight)
            local_similarity = fuzz.ratio(local1, local2) / 100.0
            
            # Weighted combination
            return (domain_similarity * 0.6) + (local_similarity * 0.4)
            
        except ValueError:
            # Invalid email format, use general similarity
            return fuzz.ratio(email1.lower(), email2.lower()) / 100.0
    
    def calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """
        Calculate similarity between two addresses using Levenshtein distance
        Handles street type variations and abbreviations
        """
        if not addr1 or not addr2:
            return 0.0
        
        # Normalize addresses
        norm_addr1 = self.normalize_string(addr1)
        norm_addr2 = self.normalize_string(addr2)
        
        # Exact match after normalization
        if norm_addr1 == norm_addr2:
            return 1.0
        
        # Apply address abbreviations
        norm_addr1 = self.apply_abbreviations(norm_addr1, self.business_abbreviations)
        norm_addr2 = self.apply_abbreviations(norm_addr2, self.business_abbreviations)
        
        # Check exact match after abbreviation normalization
        if norm_addr1 == norm_addr2:
            return 0.95
        
        # Calculate multiple similarity scores
        scores = []
        
        # Simple ratio
        scores.append(fuzz.ratio(norm_addr1, norm_addr2) / 100.0)
        
        # Token sort ratio (ignores word order)
        scores.append(fuzz.token_sort_ratio(norm_addr1, norm_addr2) / 100.0)
        
        # Token set ratio (ignores duplicates and order)
        scores.append(fuzz.token_set_ratio(norm_addr1, norm_addr2) / 100.0)
        
        # Partial ratio for partial matches
        scores.append(fuzz.partial_ratio(norm_addr1, norm_addr2) / 100.0)
        
        return max(scores)
    
    def calculate_city_similarity(self, city1: str, city2: str) -> float:
        """
        Calculate similarity between two city names using Levenshtein distance
        Handles common city abbreviations
        """
        if not city1 or not city2:
            return 0.0
        
        # Normalize cities
        norm_city1 = self.normalize_string(city1)
        norm_city2 = self.normalize_string(city2)
        
        # Exact match
        if norm_city1 == norm_city2:
            return 1.0
        
        # Apply city abbreviations
        norm_city1 = self.apply_abbreviations(norm_city1, self.city_abbreviations)
        norm_city2 = self.apply_abbreviations(norm_city2, self.city_abbreviations)
        
        # Check exact match after abbreviation normalization
        if norm_city1 == norm_city2:
            return 0.95
        
        # Use Levenshtein distance
        return fuzz.ratio(norm_city1, norm_city2) / 100.0
    
    def calculate_website_similarity(self, website1: str, website2: str) -> float:
        """
        Calculate similarity between two website addresses using Levenshtein distance
        """
        if not website1 or not website2:
            return 0.0
        
        # Normalize websites
        website1 = re.sub(r'^https?://', '', website1.lower().strip())
        website2 = re.sub(r'^https?://', '', website2.lower().strip())
        
        # Remove www prefix
        website1 = re.sub(r'^www\.', '', website1)
        website2 = re.sub(r'^www\.', '', website2)
        
        # Exact match
        if website1 == website2:
            return 1.0
        
        # Domain match
        try:
            domain1 = website1.split('/')[0]
            domain2 = website2.split('/')[0]
            
            if domain1 == domain2:
                return 0.95
            
            # Use Levenshtein distance for domain similarity
            domain_similarity = fuzz.ratio(domain1, domain2) / 100.0
            
            # Check for subdomain variations
            if domain1.endswith(domain2) or domain2.endswith(domain1):
                return 0.9
            
            return domain_similarity
            
        except (IndexError, AttributeError):
            return fuzz.ratio(website1, website2) / 100.0
    
    # New methods for specific identity resolution rules
    
    def calculate_contact_identity_score(self, contact1: dict, contact2: dict) -> float:
        """
        Calculate identity resolution score for contacts based on new rules:
        1. Fuzzy First Name match - probability 0.8
        2. Exact Last Name match - probability 1.0
        3. Case insensitive exact Email match
        4. All digits of phone number match
        
        Args:
            contact1, contact2: Contact dictionaries with FIRST_NAME, LAST_NAME, EMAIL, PHONE
            
        Returns:
            float: Overall identity score (0.0 to 1.0)
        """
        scores = []
        
        # Rule 1: Fuzzy First Name match (probability 0.8)
        first_name1 = contact1.get('FIRST_NAME', '')
        first_name2 = contact2.get('FIRST_NAME', '')
        if first_name1 and first_name2:
            first_similarity = self.calculate_first_name_similarity(first_name1, first_name2)
            if first_similarity >= 0.8:  # 80% threshold
                scores.append(0.8)  # Probability weight
            else:
                scores.append(0.0)
        
        # Rule 2: Exact Last Name match (probability 1.0)
        last_name1 = contact1.get('LAST_NAME', '')
        last_name2 = contact2.get('LAST_NAME', '')
        if last_name1 and last_name2:
            if last_name1.lower().strip() == last_name2.lower().strip():
                scores.append(1.0)  # Exact match gets full probability
            else:
                scores.append(0.0)
        
        # Rule 3: Case insensitive exact Email match
        email1 = contact1.get('EMAIL', '')
        email2 = contact2.get('EMAIL', '')
        if email1 and email2:
            if email1.lower().strip() == email2.lower().strip():
                scores.append(1.0)  # Exact match
            else:
                scores.append(0.0)
        
        # Rule 4: All digits of phone number match
        phone1 = contact1.get('PHONE', '')
        phone2 = contact2.get('PHONE', '')
        if phone1 and phone2:
            digits1 = re.sub(r'[^\d]', '', phone1)
            digits2 = re.sub(r'[^\d]', '', phone2)
            if digits1 == digits2 and len(digits1) > 0:
                scores.append(1.0)  # All digits match
            else:
                scores.append(0.0)
        
        # Return average of all applicable rules
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.0
    
    def calculate_first_name_similarity(self, first1: str, first2: str) -> float:
        """
        Calculate fuzzy similarity for first names with 80% threshold
        Uses Levenshtein distance with common name variations
        """
        if not first1 or not first2:
            return 0.0
        
        # Normalize names
        norm_first1 = self.normalize_string(first1)
        norm_first2 = self.normalize_string(first2)
        
        # Exact match
        if norm_first1 == norm_first2:
            return 1.0
        
        # Common name variations mapping
        name_variations = {
            'john': ['jon', 'johnny', 'johnathan', 'jonathan'],
            'michael': ['mike', 'micheal', 'mick', 'mickey'],
            'david': ['dave', 'davey', 'davy'],
            'robert': ['rob', 'bob', 'bobby', 'robbie'],
            'james': ['jim', 'jimmy', 'jamie'],
            'william': ['bill', 'will', 'billy', 'willy'],
            'richard': ['rick', 'rich', 'dick', 'ricky'],
            'charles': ['chuck', 'charlie', 'charley'],
            'thomas': ['tom', 'tommy', 'thom'],
            'christopher': ['chris', 'cristopher', 'kristopher'],
            'daniel': ['dan', 'danny', 'dane'],
            'matthew': ['matt', 'matty', 'mathew'],
            'anthony': ['tony', 'antony', 'anton'],
            'mark': ['marc', 'marcus', 'marco'],
            'donald': ['don', 'donny', 'donal'],
            'steven': ['steve', 'stevie', 'stephen'],
            'paul': ['paulo', 'pablo', 'paolo'],
            'andrew': ['andy', 'andre', 'drew'],
            'joshua': ['josh', 'josiah', 'jose'],
            'kenneth': ['ken', 'kenny', 'kent'],
            'mary': ['marie', 'maria', 'marie'],
            'patricia': ['pat', 'patty', 'tricia'],
            'jennifer': ['jen', 'jenny', 'jenn'],
            'linda': ['lynn', 'lindy'],
            'elizabeth': ['liz', 'beth', 'betty', 'lizzie'],
            'barbara': ['barb', 'barbie'],
            'susan': ['sue', 'suzie', 'susie'],
            'jessica': ['jess', 'jessie'],
            'sarah': ['sara', 'sally'],
            'karen': ['karin', 'karyn'],
            'nancy': ['nan', 'nancy'],
            'lisa': ['liz', 'lizzie'],
            'betty': ['beth', 'betsy'],
            'helen': ['helena', 'lena'],
            'sandra': ['sandy', 'sandi'],
            'donna': ['donnie'],
            'carol': ['caroline', 'carrie'],
            'ruth': ['ruthie'],
            'sharon': ['shari', 'sherry'],
            'michelle': ['michelle', 'micki'],
            'laura': ['laurie', 'lora'],
            'sarah': ['sara', 'sally'],
            'kimberly': ['kim', 'kimmy'],
            'deborah': ['deb', 'debbie'],
            'dorothy': ['dot', 'dottie'],
            'lisa': ['liz', 'lizzie'],
            'nancy': ['nan', 'nancy'],
            'karen': ['karin', 'karyn'],
            'betty': ['beth', 'betsy'],
            'helen': ['helena', 'lena'],
            'sandra': ['sandy', 'sandi'],
            'donna': ['donnie'],
            'carol': ['caroline', 'carrie'],
            'ruth': ['ruthie'],
            'sharon': ['shari', 'sherry'],
            'michelle': ['michelle', 'micki'],
            'laura': ['laurie', 'lora']
        }
        
        # Check for known variations
        for base_name, variations in name_variations.items():
            if norm_first1 == base_name and norm_first2 in variations:
                return 0.9
            if norm_first2 == base_name and norm_first1 in variations:
                return 0.9
            if norm_first1 in variations and norm_first2 in variations:
                return 0.85
        
        # Handle abbreviations (J. vs John)
        if (len(norm_first1) == 1 and norm_first2.startswith(norm_first1)) or \
           (len(norm_first2) == 1 and norm_first1.startswith(norm_first2)):
            return 0.9
        
        # Use Levenshtein distance
        similarity = fuzz.ratio(norm_first1, norm_first2) / 100.0
        
        # Also check partial ratio for partial matches
        partial_similarity = fuzz.partial_ratio(norm_first1, norm_first2) / 100.0
        
        return max(similarity, partial_similarity)
    
    def calculate_account_identity_score(self, account1: dict, account2: dict) -> float:
        """
        Calculate identity resolution score for accounts based on new rules:
        1. Create a field ENTERPRISE_ID if it does not exist, match exact on this field
        
        Args:
            account1, account2: Account dictionaries with ENTERPRISE_ID
            
        Returns:
            float: Overall identity score (0.0 to 1.0)
        """
        # Rule 1: Exact ENTERPRISE_ID match
        enterprise_id1 = account1.get('ENTERPRISE_ID', '')
        enterprise_id2 = account2.get('ENTERPRISE_ID', '')
        
        if enterprise_id1 and enterprise_id2:
            if enterprise_id1.strip() == enterprise_id2.strip():
                return 1.0  # Exact match
            else:
                return 0.0  # No match
        else:
            return 0.0  # Missing ENTERPRISE_ID
