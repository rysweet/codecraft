#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bootstrap.py

This module provides a streamlined, event-driven intake flow that captures and centralizes
all relevant user data into a single source of truth. It exposes functions to initialize
the system, handle dynamic input gathering, manage events, and offer immediate feedback
loops. The design aims to:

• Eliminate inefficient back-and-forth: Provide a single progressive-intake flow that
  captures each relevant data piece once.

• Reduce cognitive load: Dynamically present only necessary fields and offer real-time
  contextual nudges to guide users and stakeholders.

• Implement an event-driven architecture: Publish all meaningful user actions as events;
  downstream services subscribe and react in near-real time, ensuring context-rich insights
  are immediately available for continued user interaction.

• Maintain a single source of truth store: Continuously enrich a centralized data record,
  ensuring updates are instantly reflected without redundant data entries.

• Provide transparent feedback loops: Present adaptive summaries or previews inline so that
  users can see how newly provided information impacts their overall flow without losing focus.
"""

import uuid
from typing import Any, Callable, Dict, List, Optional

# Global store simulating the single source of truth
_SINGLE_SOURCE_OF_TRUTH: Dict[str, Any] = {}

# In-memory structure to hold event subscriptions:
# event_name -> list of callables
_EVENT_SUBSCRIBERS: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}


def init_app(config: Dict[str, Any]) -> None:
    """
    Initialize the application with the given configuration.

    This sets up any required global structures, attaches them to the single
    source of truth, and prepares the system for dynamic data capture and
    event-driven operations.

    Args:
        config: A dictionary containing any application-wide settings required
                for initialization.
    """
    _SINGLE_SOURCE_OF_TRUTH.update(config)
    _setup_event_system()
    _publish_event("app_initialized", {"message": "Application initialized", "config": config})


def unify_input_flow(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine newly provided inputs into the single source of truth while presenting
    only fields strictly necessary for the current context. Optionally trigger
    feedback events if the new inputs enrich or alter existing data.

    Args:
        inputs: A dictionary representing user-provided data at a given step
                of the intake flow.

    Returns:
        A dictionary reflecting the current state of the single source of truth
        after merging in new information.
    """
    merged_data = {}
    for key, value in inputs.items():
        # If new input is relevant or modifies existing data, handle accordingly
        if _SINGLE_SOURCE_OF_TRUTH.get(key) != value:
            _SINGLE_SOURCE_OF_TRUTH[key] = value
            merged_data[key] = value

    if merged_data:
        # If there's any meaningful update, publish an event
        _publish_event("input_updated", {"updated_fields": merged_data})

    return dict(_SINGLE_SOURCE_OF_TRUTH)


def handle_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Publish a high-level user or system event with the given type and data.
    This function notifies all subscribers listening for this event type,
    providing them near-real-time context about user actions.

    Args:
        event_type: The string identifier representing the event category.
        data: A dictionary of contextual information describing the event.
    """
    _publish_event(event_type, data)


def subscribe_to_event(event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
    """
    Register a callback function to be invoked whenever an event of the specified
    type is published. Callbacks receive the event's data payload, enabling them
    to enrich or act upon the information.

    Args:
        event_type: The string identifier representing the event category.
        callback: A callable that takes a dictionary argument (the event data).
    """
    if event_type not in _EVENT_SUBSCRIBERS:
        _EVENT_SUBSCRIBERS[event_type] = []
    _EVENT_SUBSCRIBERS[event_type].append(callback)


def get_current_state() -> Dict[str, Any]:
    """
    Retrieve a snapshot of the current single source of truth data.

    Returns:
        A dictionary reflecting the entire known application state.
    """
    return dict(_SINGLE_SOURCE_OF_TRUTH)


def _setup_event_system() -> None:
    """
    Internal helper to initialize or reset event subscriptions. Ensures that
    each invocation starts with a clean event registry.
    """
    _EVENT_SUBSCRIBERS.clear()


def _publish_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Internal helper to broadcast an event to all subscribed callbacks, enriching
    the event data with a unique identifier and timestamp.

    Args:
        event_type: A string representing the event category.
        data: The event data to be published.
    """
    subscribers = _EVENT_SUBSCRIBERS.get(event_type, [])
    event_id = str(uuid.uuid4())
    event_payload = {
        "event_id": event_id,
        "event_type": event_type,
        "data": data,
    }

    for callback in subscribers:
        callback(event_payload)