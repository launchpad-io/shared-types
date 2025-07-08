"""
Profile service for TikTok Shop Creator CRM
Handles user profile management, updates, and completion tracking.
"""

from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserRole
from app.schemas.user import (
    PersonalInfoUpdate,
    AddressUpdate,
    SocialMediaUpdate,
    CreatorDetailsUpdate,
    CompanyDetailsUpdate,
    ProfileCompletionItem
)
from app.utils.logging import get_logger
from app.core.security import verify_password, get_password_hash
# from app.services.message_service.sms_service import SMSService  # Comment out for now

logger = get_logger(__name__)


class ProfileService:
    """Service for managing user profiles and completion tracking"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        # self.sms_service = SMSService()  # Comment out for now
    
    async def get_user_profile(self, user_id: UUID) -> Optional[User]:
        """
        Get complete user profile with all relationships.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            User object with loaded relationships or None
        """
        try:
            result = await self.session.execute(
                select(User)
                .options(
                    selectinload(User.badges),
                    selectinload(User.audience_demographics)
                )
                .where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update last activity timestamp
                user.last_login = datetime.utcnow()
                await self.session.commit()
                
            return user
        except Exception as e:
            logger.error(f"Error fetching user profile {user_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def update_profile_bulk(
        self, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> User:
        """
        Update multiple profile fields at once.
        
        Args:
            user_id: UUID of the user
            update_data: Dictionary of fields to update
            
        Returns:
            Updated user object
            
        Raises:
            ValueError: If user not found or invalid data
        """
        try:
            # Get user
            user = await self.get_user_profile(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Filter out None values and system fields
            system_fields = {'id', 'email', 'username', 'hashed_password', 
                           'created_at', 'updated_at', 'role'}
            update_data = {
                k: v for k, v in update_data.items() 
                if v is not None and k not in system_fields
            }
            
            # Update user fields
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            # Update profile completion
            user.update_profile_completion()
            
            # Save changes
            await self.session.commit()
            await self.session.refresh(user)
            
            logger.info(f"Updated profile for user {user_id}: {list(update_data.keys())}")
            return user
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating profile bulk for {user_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def update_personal_info(
        self, 
        user_id: UUID, 
        personal_info: PersonalInfoUpdate
    ) -> User:
        """
        Update user's personal information.
        
        Args:
            user_id: UUID of the user
            personal_info: Personal information to update
            
        Returns:
            Updated user object
        """
        update_data = personal_info.dict(exclude_unset=True)
        
        # Validate age if date_of_birth is provided
        if 'date_of_birth' in update_data and update_data['date_of_birth']:
            age = self._calculate_age(update_data['date_of_birth'])
            if age < 13:
                raise ValueError("User must be at least 13 years old")
        
        return await self.update_profile_bulk(user_id, update_data)
    
    async def update_address(
        self, 
        user_id: UUID, 
        address_info: AddressUpdate
    ) -> User:
        """
        Update user's shipping address.
        
        Args:
            user_id: UUID of the user
            address_info: Address information to update
            
        Returns:
            Updated user object
            
        Raises:
            ValueError: If address is incomplete
        """
        update_data = address_info.dict(exclude_unset=True)
        
        # If any address field is provided, validate completeness
        address_fields = {'address_line1', 'city', 'state', 'postal_code'}
        provided_fields = set(k for k in update_data.keys() if k in address_fields)
        
        if provided_fields and provided_fields != address_fields:
            missing = address_fields - provided_fields
            # Check if user already has these fields
            user = await self.get_user_profile(user_id)
            if user:
                for field in missing:
                    if not getattr(user, field):
                        raise ValueError(
                            f"Incomplete address. Missing: {', '.join(missing)}"
                        )
        
        return await self.update_profile_bulk(user_id, update_data)
    
    async def update_social_media(
        self, 
        user_id: UUID, 
        social_info: SocialMediaUpdate
    ) -> User:
        """
        Update user's social media handles.
        
        Args:
            user_id: UUID of the user
            social_info: Social media handles to update
            
        Returns:
            Updated user object
        """
        update_data = social_info.dict(exclude_unset=True)
        
        # Normalize handles
        for field in ['tiktok_handle', 'instagram_handle']:
            if field in update_data and update_data[field]:
                # Remove @ symbol if present
                update_data[field] = update_data[field].lstrip('@')
        
        return await self.update_profile_bulk(user_id, update_data)
    
    async def update_creator_details(
        self, 
        user_id: UUID, 
        creator_details: CreatorDetailsUpdate
    ) -> User:
        """
        Update creator-specific details.
        
        Args:
            user_id: UUID of the user
            creator_details: Creator information to update
            
        Returns:
            Updated user object
            
        Raises:
            ValueError: If user is not a creator
        """
        # Verify user is a creator
        user = await self.get_user_profile(user_id)
        if not user or user.role != UserRole.CREATOR:
            raise ValueError("User must be a creator to update creator details")
        
        update_data = creator_details.dict(exclude_unset=True)
        return await self.update_profile_bulk(user_id, update_data)
    
    async def update_company_details(
        self, 
        user_id: UUID, 
        company_details: CompanyDetailsUpdate
    ) -> User:
        """
        Update agency/brand company details.
        
        Args:
            user_id: UUID of the user
            company_details: Company information to update
            
        Returns:
            Updated user object
            
        Raises:
            ValueError: If user is not an agency or brand
        """
        # Verify user is agency or brand
        user = await self.get_user_profile(user_id)
        if not user or user.role not in [UserRole.AGENCY, UserRole.BRAND]:
            raise ValueError("User must be an agency or brand to update company details")
        
        update_data = company_details.dict(exclude_unset=True)
        return await self.update_profile_bulk(user_id, update_data)
    
    async def update_preferences(
        self, 
        user_id: UUID, 
        preferences: Dict[str, Any]
    ) -> User:
        """
        Update user's notification preferences.
        
        Args:
            user_id: UUID of the user
            preferences: Notification preferences
            
        Returns:
            Updated user object
        """
        user = await self.get_user_profile(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Merge with existing preferences
        current_prefs = user.notification_preferences or {}
        current_prefs.update(preferences)
        
        return await self.update_profile_bulk(
            user_id, 
            {'notification_preferences': current_prefs}
        )
    
    async def get_profile_completion_status(
        self, 
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get detailed profile completion status.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dictionary with completion details and suggestions
        """
        user = await self.get_user_profile(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Define required fields by section
        sections = self._get_profile_sections(user.role)
        
        completion_items = []
        missing_fields = []
        completed_fields = 0
        total_fields = 0
        
        # Check each section
        for section_name, section_data in sections.items():
            fields = section_data['fields']
            weight = section_data['weight']
            required = section_data.get('required', True)
            
            if not required and user.role not in section_data.get('roles', []):
                continue
            
            # Count completed fields in section
            section_complete = 0
            section_total = len(fields)
            total_fields += section_total
            
            for field in fields:
                value = getattr(user, field, None)
                if value:
                    section_complete += 1
                    completed_fields += 1
                else:
                    missing_fields.append(field)
            
            # Create completion item
            completion_items.append(
                ProfileCompletionItem(
                    name=section_data['name'],
                    completed=(section_complete == section_total),
                    description=section_data['description'],
                    category=section_name
                )
            )
        
        # Calculate percentage
        percentage = user.calculate_profile_completion()
        
        # Generate next steps
        next_steps = self._generate_next_steps(missing_fields, user.role)
        
        return {
            'completion_percentage': percentage,
            'total_fields': total_fields,
            'completed_fields': completed_fields,
            'missing_fields': missing_fields,
            'completion_items': completion_items,
            'next_steps': next_steps
        }
    
    async def request_phone_verification(
        self, 
        user_id: UUID, 
        phone_number: str
    ) -> Dict[str, Any]:
        """
        Send phone verification code via SMS.
        
        Args:
            user_id: UUID of the user
            phone_number: Phone number to verify
            
        Returns:
            Verification details
            
        Raises:
            ValueError: If rate limited or invalid phone
        """
        # Check rate limiting (implement in production)
        # For now, we'll just validate and send
        
        # Generate 6-digit code
        import random
        code = str(random.randint(100000, 999999))
        
        # Store code in cache/db with expiration
        # TODO: Implement proper code storage with Redis
        
        # Send SMS
        try:
            # await self.sms_service.send_verification_code(phone_number, code)
            logger.info(f"Would send verification code {code} to {phone_number}")  # Placeholder
            
            # Update user's phone (unverified)
            await self.update_profile_bulk(user_id, {'phone': phone_number})
            
            return {
                'message': 'Verification code sent',
                'expires_in': 300  # 5 minutes
            }
        except Exception as e:
            logger.error(f"Failed to send verification SMS: {str(e)}")
            raise ValueError("Failed to send verification code")
    
    async def verify_phone_number(
        self, 
        user_id: UUID, 
        code: str
    ) -> bool:
        """
        Verify phone number with code.
        
        Args:
            user_id: UUID of the user
            code: Verification code
            
        Returns:
            True if verified successfully
        """
        # TODO: Implement proper verification with code storage
        # For now, return True for demo
        
        # Mark phone as verified in user profile
        # This would be a separate field in production
        
        return True
    
    async def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
        role: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List users with pagination and filtering.
        
        Args:
            page: Page number
            per_page: Items per page
            role: Filter by role
            search: Search term
            
        Returns:
            Paginated user list
        """
        try:
            # Build query
            query = select(User)
            
            # Apply filters
            filters = []
            if role:
                filters.append(User.role == role)
            if search:
                search_term = f"%{search}%"
                filters.append(
                    or_(
                        User.username.ilike(search_term),
                        User.email.ilike(search_term),
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term)
                    )
                )
            
            if filters:
                query = query.where(and_(*filters))
            
            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.session.execute(query)
            users = result.scalars().all()
            
            # Calculate pages
            pages = (total + per_page - 1) // per_page
            
            return {
                'users': users,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages
            }
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            raise
    
    # Helper methods
    def _calculate_age(self, birth_date: date) -> int:
        """Calculate age from birth date"""
        today = date.today()
        return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
    
    def _get_profile_sections(self, role: UserRole) -> Dict[str, Dict[str, Any]]:
        """Get profile sections based on role"""
        sections = {
            'basic': {
                'name': 'Basic Information',
                'description': 'Email, username, and name',
                'fields': ['email', 'username', 'first_name', 'last_name', 'phone'],
                'weight': 40,
                'required': True
            },
            'personal': {
                'name': 'Personal Information',
                'description': 'Date of birth, gender, bio, and profile image',
                'fields': ['date_of_birth', 'gender', 'profile_image_url', 'bio'],
                'weight': 20,
                'required': True
            },
            'address': {
                'name': 'Shipping Address',
                'description': 'Required for receiving products',
                'fields': ['address_line1', 'city', 'state', 'postal_code'],
                'weight': 20,
                'required': True
            }
        }
        
        # Add role-specific sections
        if role == UserRole.CREATOR:
            sections['role_specific'] = {
                'name': 'Creator Details',
                'description': 'Social media and content information',
                'fields': ['tiktok_handle', 'content_niche', 'follower_count'],
                'weight': 20,
                'required': True,
                'roles': [UserRole.CREATOR]
            }
        elif role in [UserRole.AGENCY, UserRole.BRAND]:
            sections['role_specific'] = {
                'name': 'Company Details',
                'description': 'Company information and tax ID',
                'fields': ['company_name', 'website_url', 'tax_id'],
                'weight': 20,
                'required': True,
                'roles': [UserRole.AGENCY, UserRole.BRAND]
            }
        
        return sections
    
    def _generate_next_steps(
        self, 
        missing_fields: List[str], 
        role: UserRole
    ) -> List[str]:
        """Generate helpful next steps based on missing fields"""
        next_steps = []
        
        # Priority suggestions
        if 'phone' in missing_fields:
            next_steps.append("Add your phone number for important notifications")
        
        if any(f in missing_fields for f in ['address_line1', 'city', 'state', 'postal_code']):
            next_steps.append("Complete your shipping address to receive products")
        
        if role == UserRole.CREATOR:
            if 'tiktok_handle' in missing_fields:
                next_steps.append("Connect your TikTok account to track performance")
            if 'content_niche' in missing_fields:
                next_steps.append("Select your content niche for better campaign matching")
        
        if role in [UserRole.AGENCY, UserRole.BRAND]:
            if 'company_name' in missing_fields:
                next_steps.append("Add your company name for professional presence")
            if 'tax_id' in missing_fields:
                next_steps.append("Provide tax ID for payment processing")
        
        if 'profile_image_url' in missing_fields:
            next_steps.append("Upload a profile photo to personalize your account")
        
        # Limit to top 3 suggestions
        return next_steps[:3]