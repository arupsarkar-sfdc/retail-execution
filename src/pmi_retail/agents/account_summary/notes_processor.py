"""
Account Notes Processor
Processes and structures account-related notes for LLM consumption
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from langchain.schema import Document

logger = logging.getLogger(__name__)


class AccountNotesProcessor:
    """Processes and structures account-related notes for AI analysis"""
    
    def __init__(self):
        """Initialize Account Notes Processor"""
        self.note_categories = {
            'Customer Service': ['complaint', 'issue', 'support', 'service', 'problem'],
            'Sales': ['sale', 'purchase', 'order', 'quote', 'proposal', 'deal'],
            'Support': ['help', 'assistance', 'technical', 'bug', 'error'],
            'General': ['meeting', 'call', 'email', 'follow-up', 'update'],
            'Marketing': ['campaign', 'promotion', 'offer', 'discount', 'marketing'],
            'Finance': ['payment', 'invoice', 'billing', 'credit', 'refund']
        }
    
    def process_account_notes(self, account_id: str, notes: List[Dict[str, Any]]) -> List[Document]:
        """
        Convert account notes into structured documents for vectorstore
        
        Args:
            account_id: Account ID
            notes: List of note dictionaries
            
        Returns:
            List of Document objects for vectorstore
        """
        try:
            logger.info(f"📝 Processing {len(notes)} notes for account {account_id}")
            
            documents = []
            
            for note in notes:
                # Create structured document
                doc = self._create_note_document(account_id, note)
                if doc:
                    documents.append(doc)
            
            logger.info(f"✅ Created {len(documents)} documents from notes")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Error processing notes for account {account_id}: {str(e)}")
            return []
    
    def _create_note_document(self, account_id: str, note: Dict[str, Any]) -> Optional[Document]:
        """Create a Document object from a note"""
        try:
            # Extract key information
            note_id = note.get('note_id', '')
            note_type = note.get('note_type', '')
            category = note.get('note_category', '')
            priority = note.get('note_priority', '')
            subject = note.get('subject', '')
            note_text = note.get('note_text', '')
            created_by = note.get('created_by', '')
            created_timestamp = note.get('created_timestamp', '')
            tags = note.get('tags', '')
            
            # Create comprehensive content for LLM processing
            content = self._format_note_content(note)
            
            # Create metadata
            metadata = {
                'account_id': account_id,
                'note_id': note_id,
                'note_type': note_type,
                'category': category,
                'priority': priority,
                'subject': subject,
                'created_by': created_by,
                'created_timestamp': str(created_timestamp),
                'tags': tags,
                'source': 'account_notes'
            }
            
            return Document(page_content=content, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error creating document from note {note.get('note_id', 'unknown')}: {str(e)}")
            return None
    
    def _format_note_content(self, note: Dict[str, Any]) -> str:
        """Format note content for LLM processing"""
        try:
            # Extract fields
            note_type = note.get('note_type', '')
            category = note.get('note_category', '')
            priority = note.get('note_priority', '')
            subject = note.get('subject', '')
            note_text = note.get('note_text', '')
            created_by = note.get('created_by', '')
            created_timestamp = note.get('created_timestamp', '')
            tags = note.get('tags', '')
            assigned_to = note.get('assigned_to', '')
            due_date = note.get('due_date', '')
            resolution_date = note.get('resolution_date', '')
            
            # Format timestamp
            timestamp_str = ""
            if created_timestamp:
                if isinstance(created_timestamp, str):
                    timestamp_str = created_timestamp
                else:
                    timestamp_str = created_timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # Create structured content
            content_parts = []
            
            # Header information
            if subject:
                content_parts.append(f"Subject: {subject}")
            
            if note_type:
                content_parts.append(f"Type: {note_type}")
            
            if category:
                content_parts.append(f"Category: {category}")
            
            if priority:
                content_parts.append(f"Priority: {priority}")
            
            # Main content
            if note_text:
                content_parts.append(f"Content: {note_text}")
            
            # Additional details
            if assigned_to:
                content_parts.append(f"Assigned to: {assigned_to}")
            
            if due_date:
                content_parts.append(f"Due date: {due_date}")
            
            if resolution_date:
                content_parts.append(f"Resolved: {resolution_date}")
            
            if created_by:
                content_parts.append(f"Created by: {created_by}")
            
            if timestamp_str:
                content_parts.append(f"Date: {timestamp_str}")
            
            if tags:
                content_parts.append(f"Tags: {tags}")
            
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error formatting note content: {str(e)}")
            return note.get('note_text', '')
    
    def categorize_notes(self, notes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize notes by type, priority, and topic
        
        Args:
            notes: List of note dictionaries
            
        Returns:
            Dictionary with categorized notes
        """
        try:
            categorized = {
                'by_type': {},
                'by_priority': {},
                'by_category': {},
                'by_topic': {}
            }
            
            for note in notes:
                # Categorize by type
                note_type = note.get('note_type', 'Unknown')
                if note_type not in categorized['by_type']:
                    categorized['by_type'][note_type] = []
                categorized['by_type'][note_type].append(note)
                
                # Categorize by priority
                priority = note.get('note_priority', 'Unknown')
                if priority not in categorized['by_priority']:
                    categorized['by_priority'][priority] = []
                categorized['by_priority'][priority].append(note)
                
                # Categorize by category
                category = note.get('note_category', 'Unknown')
                if category not in categorized['by_category']:
                    categorized['by_category'][category] = []
                categorized['by_category'][category].append(note)
                
                # Categorize by topic (based on content analysis)
                topic = self._identify_note_topic(note)
                if topic not in categorized['by_topic']:
                    categorized['by_topic'][topic] = []
                categorized['by_topic'][topic].append(note)
            
            logger.info(f"✅ Categorized {len(notes)} notes")
            return categorized
            
        except Exception as e:
            logger.error(f"❌ Error categorizing notes: {str(e)}")
            return {}
    
    def _identify_note_topic(self, note: Dict[str, Any]) -> str:
        """Identify the main topic of a note based on content analysis"""
        try:
            # Get text content
            subject = note.get('subject', '').lower()
            note_text = note.get('note_text', '').lower()
            category = note.get('note_category', '').lower()
            tags = note.get('tags', '').lower()
            
            # Combine all text for analysis
            combined_text = f"{subject} {note_text} {category} {tags}"
            
            # Check against predefined categories
            for topic, keywords in self.note_categories.items():
                for keyword in keywords:
                    if keyword in combined_text:
                        return topic
            
            # Default to General if no specific topic found
            return 'General'
            
        except Exception as e:
            logger.error(f"Error identifying note topic: {str(e)}")
            return 'General'
    
    def extract_key_insights(self, notes: List[Dict[str, Any]]) -> List[str]:
        """
        Extract key insights from notes for summary generation
        
        Args:
            notes: List of note dictionaries
            
        Returns:
            List of key insights
        """
        try:
            insights = []
            
            # Analyze note patterns
            high_priority_notes = [n for n in notes if n.get('note_priority') == 'High']
            recent_notes = self._get_recent_notes(notes, days=30)
            unresolved_notes = [n for n in notes if n.get('note_status') != 'Resolved']
            
            # Generate insights based on patterns
            if high_priority_notes:
                insights.append(f"High priority issues: {len(high_priority_notes)} urgent items requiring attention")
            
            if recent_notes:
                insights.append(f"Recent activity: {len(recent_notes)} notes in the last 30 days")
            
            if unresolved_notes:
                insights.append(f"Outstanding items: {len(unresolved_notes)} unresolved notes")
            
            # Analyze note categories
            category_counts = {}
            for note in notes:
                category = note.get('note_category', 'Unknown')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            if category_counts:
                top_category = max(category_counts, key=category_counts.get)
                insights.append(f"Primary focus area: {top_category} ({category_counts[top_category]} notes)")
            
            # Analyze sentiment patterns (basic keyword analysis)
            positive_keywords = ['good', 'great', 'excellent', 'satisfied', 'happy', 'success']
            negative_keywords = ['problem', 'issue', 'complaint', 'disappointed', 'frustrated', 'error']
            
            positive_count = sum(1 for note in notes 
                               if any(keyword in note.get('note_text', '').lower() 
                                     for keyword in positive_keywords))
            negative_count = sum(1 for note in notes 
                               if any(keyword in note.get('note_text', '').lower() 
                                     for keyword in negative_keywords))
            
            if positive_count > negative_count:
                insights.append("Overall sentiment: Positive customer relationship")
            elif negative_count > positive_count:
                insights.append("Overall sentiment: Some customer concerns identified")
            else:
                insights.append("Overall sentiment: Neutral customer relationship")
            
            logger.info(f"✅ Extracted {len(insights)} key insights")
            return insights
            
        except Exception as e:
            logger.error(f"❌ Error extracting key insights: {str(e)}")
            return []
    
    def _get_recent_notes(self, notes: List[Dict[str, Any]], days: int = 30) -> List[Dict[str, Any]]:
        """Get notes from the last N days"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_notes = []
            
            for note in notes:
                created_timestamp = note.get('created_timestamp')
                if created_timestamp:
                    if isinstance(created_timestamp, str):
                        try:
                            created_date = datetime.fromisoformat(created_timestamp.replace('Z', '+00:00'))
                        except:
                            continue
                    else:
                        created_date = created_timestamp
                    
                    if created_date >= cutoff_date:
                        recent_notes.append(note)
            
            return recent_notes
            
        except Exception as e:
            logger.error(f"Error getting recent notes: {str(e)}")
            return []
    
    def generate_notes_summary(self, notes: List[Dict[str, Any]]) -> str:
        """
        Generate a text summary of notes for LLM context
        
        Args:
            notes: List of note dictionaries
            
        Returns:
            Formatted text summary
        """
        try:
            if not notes:
                return "No notes available for this account."
            
            # Categorize notes
            categorized = self.categorize_notes(notes)
            
            summary_parts = []
            summary_parts.append(f"Total Notes: {len(notes)}")
            
            # Summary by type
            if categorized.get('by_type'):
                summary_parts.append("\nBy Type:")
                for note_type, type_notes in categorized['by_type'].items():
                    summary_parts.append(f"  - {note_type}: {len(type_notes)} notes")
            
            # Summary by priority
            if categorized.get('by_priority'):
                summary_parts.append("\nBy Priority:")
                for priority, priority_notes in categorized['by_priority'].items():
                    summary_parts.append(f"  - {priority}: {len(priority_notes)} notes")
            
            # Summary by category
            if categorized.get('by_category'):
                summary_parts.append("\nBy Category:")
                for category, category_notes in categorized['by_category'].items():
                    summary_parts.append(f"  - {category}: {len(category_notes)} notes")
            
            # Recent activity
            recent_notes = self._get_recent_notes(notes, days=30)
            if recent_notes:
                summary_parts.append(f"\nRecent Activity: {len(recent_notes)} notes in last 30 days")
            
            # Key insights
            insights = self.extract_key_insights(notes)
            if insights:
                summary_parts.append("\nKey Insights:")
                for insight in insights:
                    summary_parts.append(f"  - {insight}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"❌ Error generating notes summary: {str(e)}")
            return f"Error processing {len(notes)} notes: {str(e)}"
