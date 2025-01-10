"""UX designer agent that creates and updates designs."""
from typing import List, Dict, Any, Optional
import logging
import asyncio
import os
import json
from datetime import datetime

from src.agents.base_agent import BaseAgent
from src.models.task import Task, TaskStatus
from src.utils.base_logger import BaseLogger
from src.services.github_service import GitHubService
from src.utils.event_system import EventSystem
from src.utils.event_constants import CHANNELS
from src.core.messaging import create_success_response, create_error_response
from .design_system import DesignSystem
from .accessibility import AccessibilityChecker
from .pattern_library import PatternLibrary

class UXDesigner(BaseAgent):
    """UX Designer agent responsible for creating UI/UX designs."""

    def __init__(self,
                 event_system: Optional[EventSystem] = None,
                 start_listening: bool = True,
                 github_service: Optional[GitHubService] = None,
                 github_config: Optional[Any] = None):
        """Initialize the UX designer agent.

        Args:
            event_system: Optional event system instance. If not provided, will get from singleton.
            start_listening: Whether to start listening for events immediately
            github_service: Optional GitHub service instance for testing
            github_config: Optional GitHub config for testing
        """
        # Initialize base class first to set up task manager and event system
        super().__init__(model_name="gpt-4-1106-preview", start_listening=start_listening, event_system=event_system)

        # Set up designer-specific attributes
        self.designer_id = os.getenv("DESIGNER_ID")
        if not self.designer_id:
            raise RuntimeError("DESIGNER_ID environment variable is required")

        self.designer_id = self.designer_id.replace("-", "_")  # Normalize to underscore
        self.uxdesigner_id = self.designer_id  # Add this for test compatibility
        self.github = github_service or GitHubService(github_config)
        self.logger = BaseLogger(self.__class__.__name__)
        self.design_system = DesignSystem((github_config or {}).get('design_system', {}))
        self.accessibility_checker = AccessibilityChecker()
        self.pattern_library = PatternLibrary()

    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        await super().setup_events()  # This handles system and story_assigned subscriptions
        self.logger.info("Event system setup complete")
        
    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages.
        
        Args:
            message: System message data
        """
        # Log system messages but no specific handling needed
        self.logger.info(f"Received system message: {message}")
        
    async def handle_story_assigned(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment event.
        
        Args:
            data: Event data containing story details
            
        Returns:
            Dict containing status and any error details
        """
        try:
            story_id = data["story_id"]
            title = data["title"]
            description = data["description"]
            assigned_to = data["assigned_to"]
            
            self.logger.info(f"Handling story assignment: {title}")
            
            # Validate designer assignment
            if assigned_to != self.designer_id:
                self.logger.info(f"Story assigned to {assigned_to}, but I am {self.designer_id}")
                return {
                    "status": "error",
                    "message": f"Story not assigned to {self.designer_id}",
                    "error": f"Story not assigned to {self.designer_id}"
                }
            
            # Create design specs for the story
            task = Task(
                id=story_id,
                title=title,
                description=description,
                requires_ux=True,
                status=TaskStatus.IN_PROGRESS
            )
            
            # Generate design artifacts
            design_specs = self.create_design_specs(task)
            mockups = self.create_mockups(design_specs)
            
            # Format results
            results_data = {
                "design_specs": design_specs,
                "mockups": mockups
            }
            
            # Notify about design completion
            await self.event_system.publish(
                "design_completed",
                {
                    "story_id": story_id,
                    "designer_id": self.designer_id,
                    **results_data
                }
            )
            
            self.logger.info(f"Published design results for story {story_id}")
            return {"status": "success", "data": results_data}
            
        except KeyError as e:
            error_msg = f"Missing required field: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "error": error_msg
            }
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error handling story assignment: {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "error": error_msg
            }
            
    def create_design_specs(self, task: Task) -> Dict[str, Any]:
        """Create design specifications for a task.
        
        Args:
            task: The task to create design specs for
            
        Returns:
            Dict containing the design specifications
        """
        prompt = f"""Create detailed UI/UX design specifications for this task:

Title: {task.title}
Description: {task.description}

Generate a comprehensive design specification including:
1. User Interface Components
2. Layout Structure
3. Color Scheme
4. Typography
5. Interaction Patterns
6. Responsive Design Considerations
7. Accessibility Requirements
8. Design System Integration

Format the response as a JSON object with these sections.
"""
        
        try:
            response = self.model.generate_response(prompt)
            specs = json.loads(response)
            
            # Validate required sections
            required_sections = [
                "ui_components",
                "layout",
                "color_scheme",
                "typography",
                "interactions",
                "responsive_design",
                "accessibility",
                "design_system"
            ]
            
            for section in required_sections:
                if section not in specs:
                    specs[section] = {"note": f"Default {section} specifications applied"}
            
            return specs
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse design specs: {str(e)}")
            return {
                "error": "Failed to generate valid design specifications",
                "fallback_specs": {
                    "ui_components": {"type": "basic", "components": ["default layout"]},
                    "layout": {"type": "standard", "structure": "single column"},
                    "color_scheme": {"primary": "#007bff", "secondary": "#6c757d"},
                    "typography": {"main_font": "system-ui", "scale": "default"},
                    "interactions": {"type": "standard", "patterns": ["click", "hover"]},
                    "responsive_design": {"breakpoints": ["sm", "md", "lg"]},
                    "accessibility": {"level": "WCAG 2.1 AA"},
                    "design_system": {"name": "default", "version": "1.0"}
                }
            }
        except Exception as e:
            self.logger.error(f"Error creating design specs: {str(e)}")
            return {
                "error": str(e),
                "status": "error"
            }
        
    async def create_mockups(self, design_specs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate UI mockups based on design specifications.
        
        Args:
            design_specs: Design requirements and constraints
            
        Returns:
            Dict containing mockup data, accessibility report, and metadata
        """
        try:
            # 1. Analyze requirements
            requirements = await self._analyze_requirements(design_specs)
            
            # 2. Select appropriate patterns
            patterns = await self.pattern_library.select_patterns(requirements)
            
            # 3. Generate layouts
            layouts = await self._generate_layouts(patterns, requirements)
            
            # 4. Accessibility check
            a11y_report = await self.accessibility_checker.validate(layouts)
            
            # 5. Apply design system
            final_mockups = await self.design_system.apply(layouts)
            
            return {
                "mockups": final_mockups,
                "accessibility": a11y_report,
                "patterns_used": patterns,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "design_system_version": self.design_system.version,
                    "viewport_support": ["mobile", "tablet", "desktop"]
                }
            }
            
        except Exception as e:
            self.logger.error(f"Mockup generation failed: {str(e)}")
            # Return enhanced fallback with error context
            return self._create_fallback_mockup(str(e))
        
    def _create_fallback_mockup(self, error_msg: str) -> Dict[str, Any]:
        """Create a fallback mockup in case of failure.
        
        Args:
            error_msg: Error message to include in the fallback
            
        Returns:
            Dict containing the fallback mockup
        """
        return {
            "error": "Failed to generate valid mockups",
            "fallback_mockups": {
                "desktop_layout": {"type": "basic", "viewport": "1920x1080"},
                "mobile_layout": {"type": "basic", "viewport": "375x667"},
                "component_states": {"default": True, "hover": True, "active": True},
                "user_flows": {"type": "basic", "steps": ["start", "action", "end"]},
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "design_system_version": "1.0",
                    "responsive_breakpoints": ["sm", "md", "lg"]
                }
            }
        } 