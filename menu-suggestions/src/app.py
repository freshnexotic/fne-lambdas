import json
from openai import OpenAI

def get_prompt(event_description):
    return f"""
    You will be working as a Chef and Data Parser. Below is a detailed description of your responsibilities:

    **Role 1: Chef**
    Your job is to parse the event description provided and suggest a menu from our list of menu items for the customer's event. Consider the number of guests, the type of event and the context provided if any when choosing items. Keep in mind the following packages:
    - **Basic Package:** Up to 4 food items
    - **Deluxe Package:** Up to 8 food items
    

    **Note:**
    Any additional items beyond these packages will be charged separately so keep that in mind when suggesting the menu, Deserts are not included in none of the package and can will be added separately therefore if the customer did not mention any desert in in the context you should not include any desert in the menu.
    use the following guidelines to determine the number of items to include in the menu based on the number of guests:
    15-29 people: 4 - 6 items
    30-50 people: 5 - 6 items
    50-100 people: 5 - 8 items
    100-x people: 6 - 9 items

    **Types of Events:**
    - Anniversary
    - Baby shower
    - Bar mitzvah/bat mitzvah
    - Christening/communion
    - Corporate event
    - Funeral/wake
    - Party - birthday
    - Party - other
    - Wedding

    Propose a menu for the customer's event while keeping these guidelines in mind.

    **Role 2: Data Parser**
    Parse the event description to generate a JSON format prefilled with the appropriate values. Ensure the correct format for each property.
    below is the resulting JSON format that you will need to generate:

    **Event Description Example**
    zcrm_potential_id: 5743045000015914001
    zcrm_contact_id: 5743045000015913001
    name: Stacey Kaufman
    email: staceyK1025@outlook.com
    location: Lawrence, MA, 01840
    guests: 100
    event_type: Wedding
    event datetime: 2024-10-26T18:00:00-04:00
    context: Location: Lawrence, MA, 01840 What kind of event do you need catering for? Wedding Which cuisine types would you consider? American , Italian  Which of the following do you need the caterer to provide? Dinner Roughly how many guests will you need catering for? 50-200 guests What is the proposed date of the event? Saturday October 26th, 2024 How likely are you to make a hiring decision? I'm definitely going to hire someone Additional details please use email: Looking for buffet style for 100 guests British Club Lawrence, MA for a simple Wedding celebration Additional Details: please use email: Looking for buffet style for 100 guests British Club Lawrence, MA for a simple Wedding celebration

    **Generated Json**
    {{
      "zcrm_potential_id": "5743045000015914001", // Potential or deal ID; default value: ""
      "zcrm_contact_id": "5743045000015913001", // Contact ID; default value: ""
      "name": "Stacey Kaufman", // Customer name
      "email": "staceyK1025@outlook.com", // Customer email
      "location": "Lawrence, MA, 01840", // Event location
      "guests": "100", // Number of guests if in the additional details the customer mentioned the amount of guests please use that value otherwise use a specific value that is mentioned in the range of the section "how many guests will you need catering for" in the event description keep in mind minimum guests is 30 so make sure you choose a specific value that is greater than 29 in the range mentioned in the event description also that number need to be a multiple of 5
      "event_type": "Wedding", // Event type, default value: ""
      "allergies": "None", // Allergies or dietary restrictions, default value "None"
      "beverages": "[]", // Beverages (empty array if none)
      "services": "['Buffet-Style Setup', 'Plated']", // Services (default: "['Buffet-Style Setup']")
      "menu": "[Shrimp Cocktail, Stuffed Mushrooms, etc.]", // Menu items -> add menu here
      "event_datetime": "2024-10-26T18:00:00-04:00", // Event date and time if not provided use (default time: 15:00:00-05:00)
      "equipments": "[]", // Equipments (default value [])
      "phone": "" // Phone (default value). default value: ""
    }}

    List of Menu Items:
    Appetizer/Finger food/Canapes:
    Shrimp Cocktail**
    Meatballs
    Stuffed Mushroom
    Crab Cakes
    Coconut Shrimp**
    Salsa & Chips
    Charcuterie Board
    Veggie Platter
    Fruit Platter
    Hot Crab Dip
    Hot Spinach & Artichoke Dip
    Chicken Wings
    Fried Plantains
    Fried Sweet Plantains
    
    Pasta:
    Eggplant Parmigiana Pasta
    Chicken Parmigiana Pasta
    Meatballs Pasta
    Chicken Parm Pasta
    Chicken Broccoli & Ziti Pasta
    Vegetable Lasagna
    Meat Lasagna
    Stuffed Shells Pasta
    Sausage Pepper & Onions Pasta
    Baked Macaroni & Cheese
    Veggie Pasta
    
    Sandwich and Wrap:
    Mixed Tray Of Different Sandwiches
    Pulled Pork Sandwich
    BLT Sandwich
    Tuna Melt Sandwich
    
    Meat:
    Jerk Chicken
    Curry Chicken
    Chicken Stew
    Grilled Chicken
    Fried Chicken
    Chicken Skewers
    Pulled Pork
    Grilled Pork
    Fried Pork
    Pork Skewers
    Roasted Pork
    Beef Stew
    Grilled Beef
    Beef Skewers
    Fried Goat
    Curry Goat
    Goat Stew
    Grilled Goat
    Grilled Lamb
    Lamb Stew
    
    Seafood:
    Salmon Jerk
    Salmon Honey Glazed
    Grilled Salmon
    Salmon Bites
    Grilled Shrimp
    Fried Shrimp
    Shrimp Skewers
    Shrimp Stew
    Shrimp Creole
    Grilled Cod
    Cod Stew
    Grilled Red Snapper
    Fried Red Snapper
    Red Snapper Stew
    Conch Stew
    Clam Baked
    
    Salad:
    Caesar Salad
    Greek Salad
    Fruit Salad
    Cobb Salad
    Southwest
    Pasta Salad
    Potato Salad
    
    Sides:
    White Rice
    Veggie Rice
    Plantains
    Mashed Potatoes
    Baked Potato
    Steamed Veggies
    Sauteed Veggies
    Corn On The Cob
    Rice and Red Beans
    Rice and Lima Beans
    Roasted Parm Potatoes
    
    Dessert:
    Cookies
    Brownies
    Carrot Cake
    Chocolate Cake
    Cupcakes
    Vanilla Bean Cheesecake
    
    Beverage:
    None - The hosts will provide all of the beverage
    Non-Alcoholic Beverages - (Soda - Water)
    Signature Mocktails
    Coffee/Tea Station

    Please only provide just the JSON string because this value will be passed to another function to be processed.

    # Event Description
    {event_description}
    """

# def get_event_json(event_description):
#     openai.api_key = 'sk-proj-5J1xKXrrYu1wLu1p5GuYT3BlbkFJf5OFOoVpRkIfK8ngU1Ax'
#     prompt = get_prompt(event_description)
#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "You are an assistant. Generate a menu and JSON format based on the event description provided."},
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=500,
#         temperature=0.7,
#     )

#     return response.choices[0].message['content']


def parse_response(chatGPT_response):
    start = chatGPT_response.find("{")
    end = chatGPT_response.rfind("}") + 1
    json_string = chatGPT_response[start:end]
    return json_string


def get_event_json(event_description):
    prompt = get_prompt(event_description)
    openai_api_key = 'sk-proj-5J1xKXrrYu1wLu1p5GuYT3BlbkFJf5OFOoVpRkIfK8ngU1Ax'
    client = OpenAI(api_key=openai_api_key)   
    completion = client.chat.completions.create(
        model = "gpt-3.5-turbo",
        messages = [
            {"role": "system", "content": "You are an assistant. Generate a menu and JSON format based on the event description provided."},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content.strip()

def lambda_handler(event, context):
    event_description = event.get("event_description")
    jsonObject = get_event_json(event_description)
    data = json.loads(parse_response(jsonObject))
    return {
        "statusCode": 200,
        "body": json.dumps(data),
    }
