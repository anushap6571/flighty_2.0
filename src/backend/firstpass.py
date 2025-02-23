import pandas as pd


# Common airline-related keywords and phrases for email filtering

flight_keywords = {
    # Booking related terms
    'booking_terms': [
        'booking',
        'confirmation',
        'reservation confirmation',
        'itinerary',
        'e-ticket',
        'electronic ticket',
        'flight confirmation',
        'travel confirmation',
        'booking reference',
        'confirmation number',
        'reservation number',
        'booking ID',
    ],
    
    # Flight details
    'flight_identifiers': [
        'flight number',
        'flight #',
        'flight no',
        'flight no.',
        'flight details',
        'aircraft type',
        'seat assignment',
        'seat number'
    ],
    
    # Time-related terms
    'timing_terms': [
        'departure time',
        'arrival time',
        'boarding time',
        'check-in time',
        'departure date',
        'arrival date',
        'scheduled departure',
        'scheduled arrival',
        'boarding starts',
        'gate closes'
    ],
    
    # Location-related terms
    'location_terms': [
        'terminal',
        'gate',
        'departure gate',
        'arrival terminal',
        'airport code',
        'departure from',
        'arriving at'
    ],
    
    # Travel documents
    'document_terms': [
        'boarding pass',
        'travel document',
        'baggage claim',
        'check-in',
        'online check-in',
        'mobile boarding pass',
        'TSA'
    ],
    
    # Common airline actions
    'action_terms': [
        'check in online',
        'print boarding pass',
        'manage booking',
        'view reservation',
        'select seats',
        'add baggage',
        'flight status'
    ],
    
    # Passenger information
    'passenger_terms': [
        'passenger name',
        'traveler',
        'passenger details',
        'frequent flyer',
        'loyalty number',
        'ticket number'
    ]
}

# Additional patterns that might be useful
common_patterns = [
    r'\b[A-Z]{2}\d{3,4}\b',           # Flight numbers (e.g., AA1234)
    r'\b[A-Z]{3}\b',                  # Airport codes (e.g., LAX)
    r'\b\d{2}:\d{2}\b',              # Time format (e.g., 14:30)
    r'\b[A-Z]{2}\d{6}\b',            # Booking reference formats
    r'\b\d{13}\b'                     # 13-digit ticket numbers
]



def get_airline_names() -> set:
    to_remove = ["\\N", ""]
    df = pd.read_csv('airline_codes.csv')
    df.columns = ['index', 'airline_name', 'alias', 'IATA', 'ICAO', 'callsign', 'country', 'active']
    df = df[df['active'] == 'Y']

    airline_names = df['airline_name']
    airline_names = airline_names.to_list()

    airline_names = set(airline_names)
    return airline_names



def generate_firstpass_query()-> str:
    keywords = []
    for key, value in flight_keywords.items():
        keywords.extend(value)

    airline_names = get_airline_names()

    search_query = "{" + " ".join(f'+"{w}"' for w in keywords) + "}"
    airline_query = "{" + " ".join(f'+"{w}"' for w in airline_names) + "}"
    return f'{search_query} AND {airline_query} OR filename:pdf'