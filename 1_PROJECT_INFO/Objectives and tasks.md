## Decisions

# Architecture:
    - Back end: Underlying engine for room data is Microsoft Places - restricted to core functionality of E5 licensing
    - Intermediate layer: Local (not Azure)
    - Conversational AI server side (Entra object / SD Bucket?). Account attribute. 
    - Database of all requests to book
    - Coded in Python
    - Database SQL lite
    - UI Bootstrap in open web format. 
    - Device signaling 
        - Windows
        - Mac
        - Build sample data of devices
    - 
    -
# Key features
    1. Agentic booking
        - Natural language request
         
    2. Bookable desks:
        - Dynamic allocation based on personal preference profile and team association, plus any organizational constraints.
            - Environmental preferences 
            - Sit near individual
        - Automatic check in via peripherials
        - Automatic desk recycling
    
    3. Management information:
        - Genuine no-shows (rolling average over 4-weeks)
        - Floor utilization and hot spots
        - Rolling average of free desks
    
    4. Other working spaces (if there's time)
    
    5. Rooms (not priority)
        - Dynamic meeting allocation option
        - Specific room booking option (requires approval by workplace experience)
        - Future features:
            - Split room bookings for longer periods

    - Future features:
        - Analysis of why people are avoiding desks. 



