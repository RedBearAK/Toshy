import asyncio


def get_or_create_event_loop():
    """
    Get the current event loop, creating one if necessary.
    
    Compatible with Python 3.10+ where asyncio.get_event_loop() 
    raises RuntimeError if no loop exists.
    """
    try:
        # Try to get a running loop first (Python 3.7+)
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
            # If we got here on Python 3.10+, the loop might be closed
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # Python 3.10+ with no event loop at all
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    
    return loop
