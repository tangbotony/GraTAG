GRAPH_FIELD_SEP = "<SEP>"

PROMPTS = {}

# Static routing

PROMPTS["General_scale"] = """-Goal-
Given a instruction which contain a question and relevant reference, and a list of entity types ['person', 'organism', 'organization', 'location', 'event', 'time', 'diet', 'number', 'product'], the task is to extract each type of entity step by step, and finally compile a complete list of entities. The extraction process for each entity type must strictly follow the corresponding extraction rules to identify all relevant entities in the reference that will significantly help answer the question. The output format must strictly follow the example, without any additional text or output in other formats like ```json. Additionally, do not output the details of entity extraction for each step, only the final list of entities.
- Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).
######################
- Example -
######################
Example 1:
Question: Where will President Xi Jinping's Latin American trip visit?
Input text:
At the invitation of Peruvian President Boluarte and Brazilian President Lula, Chinese President Xi Jinping will visit Peru from November 13 to 21 to attend the 31st APEC leaders' informal meeting and conduct a state visit to Peru. He will also visit Brazil to attend the 19th G20 summit and conduct a state visit. Key highlights of Xi Jinping's Latin American trip include:
Highlight 1: Xi Jinping’s sixth visit to Latin America since 2013.
Highlight 2: The Rio summit of the G20 injects Chinese strength into global governance.
Highlight 3: Xi's visit to Peru after 8 years aims to further promote China-Peru strategic partnership.
Highlight 4: Xi’s visit to Brazil after 5 years will usher in the next "Golden Fifty Years" of China-Brazil relations.
################
Output:
("Entity", "Boluarte", "person", "Peruvian President Boluarte invited Chinese President Xi Jinping to Peru to attend the APEC meeting.");
("Entity", "Lula", "person", "Brazilian President Lula invited Xi Jinping to Brazil for the G20 summit.");
("Entity", "Xi Jinping", "person", "Chinese President Xi Jinping is about to visit Peru and Brazil for meetings.");
#############################
-Real Data-
######################
instruction: {instruction}
Don't response the instruction.
Here is the extraction:

# """
# PROMPTS["General_scale"] = """-Goal-
# Given a instruction which contain a question and relevant reference, and a list of entity types ['person', 'organism', 'organization', 'location', 'event', 'time', 'diet', 'number', 'product'], the task is to extract each type of entity step by step, and finally compile a complete list of entities. The extraction process for each entity type must strictly follow the corresponding extraction rules to identify all relevant entities in the reference that will significantly help answer the question. The output format must strictly follow the example, without any additional text or output in other formats like ```json. Additionally, do not output the details of entity extraction for each step, only the final list of entities.
# - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).
# - Steps -
# Step1.-person_entity_extraction-
# Identify all person entities relevant to answering the question. For each identified person entity, extract the following information:
#    - Entity Name: The name of the entity.
#    - Entity Type: person.
#    - Entity Description: A summary of the information related to the specific person in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. Optionally, include other relevant information such as the person's identity, position, major life events, significant achievements or awards, involvement in important historical events, published works, contributions, and relationships.
# Step2.-organism_entity_extraction-
# Identify all organism entities relevant to answering the question. For each identified organism entity, extract the following information:
#    - Entity Name: The name of the entity.
#    - Entity Type: organism.
#    - Entity Description: A summary of the specific organism's information relevant to the question. Based on the material, provide the most relevant description for answering the question. You may optionally include the organism's scientific name, family, genus, order, alternative names, ecological habits and habitat, physical features, physiological traits, role in the food chain, significant research findings and applications, conservation status, and relationship with humans.
# Step3.-organization_entity_extraction-
# Identify all organizations relevant to answering the question. Note that the identified organizations should not include person entities! For each identified organization, extract the following information:
#    - Entity Name: The name of the entity.
#    - Entity Type: organization.
#    - Entity Description: A summary of the information related to the specific organization in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. For example, the extracted entity description may include the organization's name, function, goals, leadership, historical background, culture, and its role or influence in the related events. For corporate organizations, in addition to extracting the company name and function, also focus on financial data, market share, annual revenue, number of employees, and other numerical information.
# Step4.-location_entity_extraction-
# Identify all location entities relevant to answering the question. For each identified location entity, extract the following information:
#    - Entity Name: The name of the entity.
#    - Entity Type: location.
#    - Entity Description: A summary of the information related to the specific location in the context of the question. Only extract the entity descriptions that significantly help answer the question. Optionally, include basic information about the location, its historical background, significant past events, or upcoming major events.
# Step5.-event_entity_extraction-
# Identify all event entities relevant to answering the question. For each identified event entity, extract the following information:
#    - Entity Name: The name of the entity.
#    - Entity Type: event.
#    - Entity Description: Detailed information about the event and its relevance to the question. Based on the information, provide the most relevant and helpful description for answering the question. This can include the background of the event, its time, location, main participants, key activities, and its impact on related fields, society, economy, or culture.
# Step6.-time_entity_extraction-
# Identify all date and time entities relevant to answering the question. For each identified entity, extract the following information:
#    - Entity Name: The name of the entity.
#    - Entity Type: date and time.
#    - Entity Description: A summary of the specific information about the date and time relevant to the question. Based on the information, provide the most relevant and helpful description for answering the question. Include the significance of the date or time point in the context of events or activities.
 
# Step7.-diet_entity_extraction-
# Identify all diet-related entities relevant to answering the question. For each identified diet entity, extract the following information:
#    - Entity Name: The name of the entity
#    - Entity Type: diet
#    - Entity Description: A summary of the specific diet related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include diet type, ingredients, cooking methods, nutritional value, eating scenarios and times, health impacts and benefits, cultural practices, dietary restrictions, pairing and suggestions, etc.

# Step8.-number_entity_extraction-
# Identify all numerical entities relevant to answering the question. For each identified entity, extract the following information:
#    - Entity Name: The name of the entity.
#    - Entity Type: number.
#    - Entity Description: The relevance of the number to the specific event, activity, or context in the material. Based on the material, provide the most relevant description for answering the question. This could include the significance of the number, its role in policy, economy, society, etc., and its impact on event development.

# Step9.-product_entity_extraction-
# Identify all product entities relevant to answering the question. Note: Product entities are defined as specific goods or services with commercial value, including but not limited to consumer goods, electronic products, software, tools, vehicles, etc. Meetings, activities, or other non-material entities should not be considered product entities.
# For each identified product entity, extract the following information:
#    - Entity Name: The name of the entity.
#    - Entity Type: product.
#    - Entity Description: A summary of the specific product and its relevance to the question. For example, the description might include the product’s functionality, market positioning, target audience, technical specifications, price, release background, and its market performance or consumer impact.

# Step10. Return all the entities identified in the above steps as a single list, but do not show the extraction details of each step. Only output the final integrated list of entities, separated by semicolons.

# Step11. When completed, only output the final integrated list of entities without showing the details of each step. End with the completion delimiter <|COMPLETE|>.

# -Real Data-
# ######################
# instruction: {instruction}
# Don't response the instruction.
# Here is the extraction:

# """
PROMPTS["General"] = """-Goal-
Given a instruction which contain a question and relevant reference, and a list of entity types ['person', 'organism', 'organization', 'location', 'event', 'time', 'diet', 'number', 'product'], the task is to extract each type of entity step by step, and finally compile a complete list of entities. The extraction process for each entity type must strictly follow the corresponding extraction rules to identify all relevant entities in the reference that will significantly help answer the question. The output format must strictly follow the example, without any additional text or output in other formats like ```json. Additionally, do not output the details of entity extraction for each step, only the final list of entities.
- Steps -

Step1.-person_entity_extraction-
Identify all person entities relevant to answering the question. For each identified person entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: person.
   - Entity Description: A summary of the information related to the specific person in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. Optionally, include other relevant information such as the person's identity, position, major life events, significant achievements or awards, involvement in important historical events, published works, contributions, and relationships.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Where will President Xi Jinping's Latin American trip visit?
Input text:
At the invitation of Peruvian President Boluarte and Brazilian President Lula, Chinese President Xi Jinping will visit Peru from November 13 to 21 to attend the 31st APEC leaders' informal meeting and conduct a state visit to Peru. He will also visit Brazil to attend the 19th G20 summit and conduct a state visit. Key highlights of Xi Jinping's Latin American trip include:
Highlight 1: Xi Jinping’s sixth visit to Latin America since 2013.
Highlight 2: The Rio summit of the G20 injects Chinese strength into global governance.
Highlight 3: Xi's visit to Peru after 8 years aims to further promote China-Peru strategic partnership.
Highlight 4: Xi’s visit to Brazil after 5 years will usher in the next "Golden Fifty Years" of China-Brazil relations.

################
Output:
("Entity", "Boluarte", "person", "Peruvian President Boluarte invited Chinese President Xi Jinping to Peru to attend the APEC meeting.");
("Entity", "Lula", "person", "Brazilian President Lula invited Xi Jinping to Brazil for the G20 summit.");
("Entity", "Xi Jinping", "person", "Chinese President Xi Jinping is about to visit Peru and Brazil for meetings.");

#############################

Step2.-organism_entity_extraction-
Identify all organism entities relevant to answering the question. For each identified organism entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: organism.
   - Entity Description: A summary of the specific organism's information relevant to the question. Based on the material, provide the most relevant description for answering the question. You may optionally include the organism's scientific name, family, genus, order, alternative names, ecological habits and habitat, physical features, physiological traits, role in the food chain, significant research findings and applications, conservation status, and relationship with humans.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What rare animals are found in the Sichuan region?
Input text:
The Sichuan region is home to a variety of rare animals, including the giant panda (scientific name Ailuropoda melanoleuca), golden snub-nosed monkeys, Tibetan antelope, and Sichuan golden snub-nosed monkeys. These animals typically inhabit high-altitude mountainous areas, especially in regions rich in bamboo, grasslands, and dense forests. The giant panda is mainly found in the mountainous areas of Sichuan, Shaanxi, and Gansu, while the golden snub-nosed monkey prefers to live in the forests of Sichuan.
################
Output:
("Entity", "Giant Panda", "organism", "Inhabits the mountainous areas of Sichuan, Shaanxi, and Gansu, especially in areas rich in bamboo.");
("Entity", "Golden Snub-nosed Monkey", "organism", "Inhabits the forests of Sichuan.");
("Entity", "Tibetan Antelope", "organism", "Inhabits the high-altitude mountainous areas of the Sichuan region.");
("Entity", "Sichuan Golden Snub-nosed Monkey", "organism", "Inhabits the mountainous areas of the Sichuan region.");
#############################

Step3.-organization_entity_extraction-
Identify all organizations relevant to answering the question. Note that the identified organizations should not include person entities! For each identified organization, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: organization.
   - Entity Description: A summary of the information related to the specific organization in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. For example, the extracted entity description may include the organization's name, function, goals, leadership, historical background, culture, and its role or influence in the related events. For corporate organizations, in addition to extracting the company name and function, also focus on financial data, market share, annual revenue, number of employees, and other numerical information.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What are the largest technology companies in the world in 2023?
Input text:
In 2023, Apple ranked as the largest technology company globally, with annual revenue exceeding $300 billion, followed by Microsoft and Amazon, with annual revenues of about $200 billion and $150 billion, respectively. Google and Meta also hold significant positions in the market, with annual revenues of $180 billion and $120 billion, respectively.

################
Output:
("Entity", "Apple", "organization", "Apple is the largest technology company globally, with annual revenue exceeding $300 billion in 2023.");
("Entity", "Microsoft", "organization", "Microsoft is the second-largest technology company globally, with annual revenue of about $200 billion in 2023.");
("Entity", "Amazon", "organization", "Amazon is the third-largest technology company globally, with annual revenue of about $150 billion in 2023.");
("Entity", "Google", "organization", "Google is a globally renowned technology company, with annual revenue of about $180 billion in 2023.");
("Entity", "Meta", "organization", "Meta has annual revenue of about $120 billion in 2023 and holds significant influence in social media and technology.");

#############################

Step4.-location_entity_extraction-
Identify all location entities relevant to answering the question. For each identified location entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: location.
   - Entity Description: A summary of the information related to the specific location in the context of the question. Only extract the entity descriptions that significantly help answer the question. Optionally, include basic information about the location, its historical background, significant past events, or upcoming major events.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What are the host cities for the 2023 FIFA World Cup?
Input text:
The 2023 FIFA World Cup will be held in Qatar. This is Qatar’s first time hosting the World Cup, and matches will be held in multiple cities, including Doha, Lusail, Al Wakrah, Al Khor, and Umm Salal. The Qatari government has invested heavily in this event, striving to provide world-class facilities and services. Despite some controversies, Qatar is actively preparing for a smooth event.

################
Output:
("Entity", "Qatar", "location", "Qatar is the host country for the 2023 FIFA World Cup.");
("Entity", "Doha", "location", "Doha is the capital of Qatar and one of the host cities for the World Cup.");
("Entity", "Lusail", "location", "Lusail is an important city in Qatar that will host World Cup matches.");
("Entity", "Al Wakrah", "location", "Al Wakrah is a city in Qatar where World Cup matches will take place.");
("Entity", "Al Khor", "location", "Al Khor is a city in Qatar that will host World Cup matches.");
("Entity", "Umm Salal", "location", "Umm Salal is a city in Qatar where World Cup matches will be held.");

#############################

Step5.-event_entity_extraction-
Identify all event entities relevant to answering the question. For each identified event entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: event.
   - Entity Description: Detailed information about the event and its relevance to the question. Based on the information, provide the most relevant and helpful description for answering the question. This can include the background of the event, its time, location, main participants, key activities, and its impact on related fields, society, economy, or culture.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example:

Question: What economic events in April 2023 impacted foreign trade?
Input text:
The State Council Information Office held a press conference on China's import and export data for Q1 2023 (released on April 13, 2023):
According to customs statistics, China's total goods trade import and export value in the first quarter was 9.89 trillion yuan, a year-on-year increase of 4.8%. Exports were 5.65 trillion yuan, an increase of 8.4%, while imports were 4.24 trillion yuan, an increase of 0.2%. The analysis shows six key features: First, the growth rate of imports and exports improved month by month. In January, due to the Chinese New Year holiday, imports and exports decreased by 7%. February "turned positive," with an 8% increase, and in March, the year-on-year growth rate improved to 15.5%, showing a positive trend. Overall growth for the first quarter was 4.8%, accelerating by 2.6 percentage points compared to Q4 of the previous year, and the year started off smoothly. Second, the number of foreign trade enterprises increased steadily. In the first quarter, China had 457,000 foreign trade enterprises, a 5.9% increase year-on-year.

################
Output:
("Entity", "Press Conference on Q1 2023 Import and Export Data", "event", "Press conference held on April 13, 2023, by the State Council Information Office, announcing China's import and export data for Q1, including total value, growth rate, and key features, providing an analysis of foreign trade trends.");
("Entity", "Impact of the Chinese New Year on Foreign Trade", "event", "In January 2023, due to the Chinese New Year holiday, China's imports and exports decreased by 7%, leading to short-term fluctuations in foreign trade growth for the first quarter.");
("Entity", "Foreign Trade Growth Turned Positive in February 2023", "event", "In February 2023, China's foreign trade turned positive, with an 8% growth, marking an important turning point for foreign trade recovery.");
("Entity", "Foreign Trade Growth Rate Increased to 15.5% in March 2023", "event", "In March 2023, China's import and export growth rate sharply increased to 15.5%, continuing the positive trend in foreign trade.");
#############################

Step6.-time_entity_extraction-
Identify all date and time entities relevant to answering the question. For each identified entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: date and time.
   - Entity Description: A summary of the specific information about the date and time relevant to the question. Based on the information, provide the most relevant and helpful description for answering the question. Include the significance of the date or time point in the context of events or activities.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Where will President Xi Jinping’s Latin American trip visit?
Input text:
At the invitation of Peruvian President Boluarte and Brazilian President Lula, Chinese President Xi Jinping will visit Peru from November 13 to 21 to attend the 31st APEC leaders' informal meeting and conduct a state visit. He will also visit Brazil to attend the 19th G20 summit and conduct a state visit. Key highlights of Xi Jinping's Latin American trip include:
Highlight 1: Xi Jinping’s sixth visit to Latin America since 2013.
Highlight 2: The Rio summit of the G20 injects Chinese strength into global governance.
Highlight 3: Xi's visit to Peru after 8 years aims to further promote China-Peru strategic partnership.
Highlight 4: Xi’s visit to Brazil after 5 years will usher in the next "Golden Fifty Years" of China-Brazil relations.

################
Output:
("Entity", "November 13 to 21", "date and time", "Xi Jinping will visit Peru from November 13 to 21, 2024, to attend the APEC meeting and conduct a state visit.");
("Entity", "2013", "date and time", "Xi Jinping's sixth visit to Latin America since 2013.");
("Entity", "2013", "date and time", "Xi Jinping's first visit to Latin America in 2013 marked an important development in China-Latin America relations.");
("Entity", "5 years", "date and time", "Xi Jinping’s visit to Brazil comes after 5 years.");
("Entity", "8 years", "date and time", "Xi Jinping’s visit to Peru comes after 8 years.");

#############################

Step7.-diet_entity_extraction-
Identify all diet-related entities relevant to answering the question. For each identified diet entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: diet
   - Entity Description: A summary of the specific diet related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include diet type, ingredients, cooking methods, nutritional value, eating scenarios and times, health impacts and benefits, cultural practices, dietary restrictions, pairing and suggestions, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What foods can help boost immunity?
Input Text:
A diet to boost immunity should be rich in vitamin C, antioxidants, and healthy fats. For instance, citrus fruits like oranges and grapefruits contain high levels of vitamin C, which helps enhance immune system function. Dark green vegetables like spinach and broccoli are also good choices for boosting immunity, as they are rich in vitamin A, C, and iron.

################
Output:
("entity", "citrus fruits", "diet", "Citrus fruits like oranges and grapefruits are rich in vitamin C, which helps boost immune system function")；
("entity", "dark green vegetables", "diet", "Dark green vegetables like spinach and broccoli are great for immunity, rich in vitamin A, C, and iron")；
#############################

Step8.-number_entity_extraction-
Identify all numerical entities relevant to answering the question. For each identified entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: number.
   - Entity Description: The relevance of the number to the specific event, activity, or context in the material. Based on the material, provide the most relevant description for answering the question. This could include the significance of the number, its role in policy, economy, society, etc., and its impact on event development.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Which indicators or data from China’s economic operation in April 2023 reflect its growth or decline trend?
Input text:
The State Council Information Office held a press conference on China’s import and export situation in the first quarter of 2023 (released on April 13, 2023). According to customs statistics, the total value of China’s goods trade in the first quarter was 9.89 trillion yuan, a year-on-year increase of 4.8%. Exports were 5.65 trillion yuan, up by 8.4%, and imports were 4.24 trillion yuan, up by 0.2%. Detailed analysis shows six main characteristics: First, the import-export growth rate increased month by month. In January 2023, due to the Spring Festival holiday, imports and exports decreased by 7%. In February, the growth rate turned positive, with an 8% increase. In March, the year-on-year growth rate increased to 15.5%, showing a positive trend.
################
Output:
("Entity", "9.89 trillion yuan", "number", "The total value of China’s goods trade in the first quarter of 2023 was 9.89 trillion yuan.");
("Entity", "4.8%", "number", "China’s import and export trade in the first quarter of 2023 increased by 4.8% year-on-year.");
("Entity", "5.65 trillion yuan", "number", "China’s export total in the first quarter of 2023 was 5.65 trillion yuan.");
("Entity", "8.4%", "number", "China’s export increased by 8.4% year-on-year in the first quarter of 2023.");
("Entity", "4.24 trillion yuan", "number", "China’s import total in the first quarter of 2023 was 4.24 trillion yuan.");
("Entity", "0.2%", "number", "China’s import increased by 0.2% year-on-year in the first quarter of 2023.");
("Entity", "45.7 million", "number", "China had 45.7 million foreign trade enterprises in the first quarter of 2023.");
("Entity", "5.9%", "number", "The number of foreign trade enterprises in China increased by 5.9% year-on-year in the first quarter of 2023.");
("Entity", "7%", "number", "China’s imports and exports decreased by 7% in January 2023 due to the Spring Festival.");
("Entity", "8%", "number", "China’s imports and exports increased by 8% in February 2023.");
("Entity", "15.5%", "number", "China’s import and export growth rate increased to 15.5% year-on-year in March 2023.");
("Entity", "2.6 percentage points", "number", "China’s overall trade growth in the first quarter of 2023 accelerated by 2.6 percentage points compared to the last quarter of 2022.");

#############################

Step9.-product_entity_extraction-
Identify all product entities relevant to answering the question. Note: Product entities are defined as specific goods or services with commercial value, including but not limited to consumer goods, electronic products, software, tools, vehicles, etc. Meetings, activities, or other non-material entities should not be considered product entities.
For each identified product entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: product.
   - Entity Description: A summary of the specific product and its relevance to the question. For example, the description might include the product’s functionality, market positioning, target audience, technical specifications, price, release background, and its market performance or consumer impact.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What are the popular smartphones in 2023?
Input text:
Apple launched the iPhone 14 in 2023, equipped with an A16 chip and an upgraded camera system, targeted at the high-end market, with a price of around $999. Samsung’s Galaxy S23 series was also released in 2023, focusing on powerful photography features and a high refresh rate display, priced between $799 and $1199. Xiaomi’s 13 Pro, favored by consumers for its cost-effectiveness and strong performance, is priced at around $749.
################
Output:
("Entity", "iPhone 14", "product", "iPhone 14 is a smartphone released by Apple in 2023, featuring an A16 chip and an upgraded camera system, targeted at the high-end market.");
("Entity", "Galaxy S23", "product", "Galaxy S23 is a smartphone released by Samsung in 2023, focusing on powerful photography features and a high refresh rate display.");
("Entity", "Xiaomi 13 Pro", "product", "Xiaomi 13 Pro is favored by consumers in 2023 for its cost-effectiveness and strong performance.");

#############################

Step10. Return all the entities identified in the above steps as a single list, but do not show the extraction details of each step. Only output the final integrated list of entities, separated by semicolons.

Step11. When completed, only output the final integrated list of entities without showing the details of each step. End with the completion delimiter <|COMPLETE|>.

-Real Data-
######################
instruction: {instruction}
Don't response the instruction.
Here is the extraction:

"""
PROMPTS["Bio"] = """-Goal-
Given a instruction which contain a question and relevant reference, and a list of entity types ['person', 'organism', 'symptom', 'disease', 'drug', 'technique', 'number', 'device', 'operation'], the task is to extract each type of entity step by step, and finally compile a complete list of entities. The extraction process for each entity type must strictly follow the corresponding extraction rules to identify all relevant entities in the documents that will significantly help answer the question. The output format must strictly follow the example, without any additional text or output in other formats like ```json. Additionally, do not output the details of entity extraction for each step, only the final list of entities.
- Steps -

Step1.-person_entity_extraction-
Identify all person entities relevant to answering the question. For each identified person entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: person.
   - Entity Description: A summary of the information related to the specific person in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. Optionally, include other relevant information such as the person's identity, position, major life events, significant achievements or awards, involvement in important historical events, published works, contributions, and relationships.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Where will President Xi Jinping's Latin American trip visit?
Input text:
At the invitation of Peruvian President Boluarte and Brazilian President Lula, Chinese President Xi Jinping will visit Peru from November 13 to 21 to attend the 31st APEC leaders' informal meeting and conduct a state visit to Peru. He will also visit Brazil to attend the 19th G20 summit and conduct a state visit. Key highlights of Xi Jinping's Latin American trip include:
Highlight 1: Xi Jinping’s sixth visit to Latin America since 2013.
Highlight 2: The Rio summit of the G20 injects Chinese strength into global governance.
Highlight 3: Xi's visit to Peru after 8 years aims to further promote China-Peru strategic partnership.
Highlight 4: Xi’s visit to Brazil after 5 years will usher in the next "Golden Fifty Years" of China-Brazil relations.

################
Output:
("Entity", "Boluarte", "person", "Peruvian President Boluarte invited Chinese President Xi Jinping to Peru to attend the APEC meeting.");
("Entity", "Lula", "person", "Brazilian President Lula invited Xi Jinping to Brazil for the G20 summit.");
("Entity", "Xi Jinping", "person", "Chinese President Xi Jinping is about to visit Peru and Brazil for meetings.");

#############################

Step2.-organism_entity_extraction-
Identify all organism entities relevant to answering the question. For each identified organism entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: organism.
   - Entity Description: A summary of the specific organism's information relevant to the question. Based on the material, provide the most relevant description for answering the question. You may optionally include the organism's scientific name, family, genus, order, alternative names, ecological habits and habitat, physical features, physiological traits, role in the food chain, significant research findings and applications, conservation status, and relationship with humans.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What rare animals are found in the Sichuan region?
Input text:
The Sichuan region is home to a variety of rare animals, including the giant panda (scientific name Ailuropoda melanoleuca), golden snub-nosed monkeys, Tibetan antelope, and Sichuan golden snub-nosed monkeys. These animals typically inhabit high-altitude mountainous areas, especially in regions rich in bamboo, grasslands, and dense forests. The giant panda is mainly found in the mountainous areas of Sichuan, Shaanxi, and Gansu, while the golden snub-nosed monkey prefers to live in the forests of Sichuan.
################
Output:
("Entity", "Giant Panda", "organism", "Inhabits the mountainous areas of Sichuan, Shaanxi, and Gansu, especially in areas rich in bamboo.");
("Entity", "Golden Snub-nosed Monkey", "organism", "Inhabits the forests of Sichuan.");
("Entity", "Tibetan Antelope", "organism", "Inhabits the high-altitude mountainous areas of the Sichuan region.");
("Entity", "Sichuan Golden Snub-nosed Monkey", "organism", "Inhabits the mountainous areas of the Sichuan region.");
#############################

Step3.-symptom_entity_extraction-
Identify all symptom entities relevant to answering the question. For each identified symptom entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: symptom
   - Entity Description: A summary of the specific symptom related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include symptom type, severity, appearance, duration, accompanying symptoms, possible causes, diagnosis, and impacts.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What potential health issues might be indicated by chronic fatigue?
Input Text:
Chronic fatigue may be related to various diseases, such as chronic fatigue syndrome, anemia, hypothyroidism, depression, and diabetes. Common symptoms include fatigue, dizziness, difficulty concentrating, dry skin, weight changes, and poor cold tolerance. Emotional fluctuations and insomnia may also be signs of depression.

################
Output:
("entity", "fatigue", "symptom", "Chronic fatigue may be related to chronic fatigue syndrome, anemia, hypothyroidism, depression, and diabetes")；
("entity", "weakness", "symptom", "Weakness may be related to fatigue, anemia, hypothyroidism, etc.")；
("entity", "dizziness", "symptom", "Dizziness may accompany chronic fatigue and indicate anemia or thyroid issues")；
("entity", "difficulty concentrating", "symptom", "Difficulty concentrating may be related to fatigue, depression, or diabetes")；
#############################

Step4.-disease_entity_extraction-
Identify all disease entities relevant to answering the question. For each identified disease entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: disease
   - Entity Description: A summary of the specific disease related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include disease type, causes, clinical symptoms, diagnosis methods, treatments, epidemiology, prevention, related risks, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What are the symptoms of hypertension?
Input Text:
Hypertension is a common chronic disease that usually does not show obvious symptoms, but as the condition progresses, symptoms such as headaches, dizziness, fatigue, and blurred vision may occur. In severe cases, high blood pressure can lead to complications like heart disease, stroke, and kidney disease. Treatment methods for hypertension include medication and lifestyle interventions such as using antihypertensive drugs, reducing salt intake, increasing exercise, and losing weight.

################
Output:
("entity", "hypertension", "disease", "Hypertension usually has no obvious symptoms, but as the condition progresses, symptoms such as headaches, dizziness, and fatigue may occur")；
("entity", "heart disease", "disease", "Hypertension may lead to heart disease and other complications")；
("entity", "stroke", "disease", "Hypertension may lead to stroke and other severe complications")；
("entity", "kidney disease", "disease", "Hypertension may lead to kidney disease and other complications")；
#############################

Step5.-drug_entity_extraction-
Identify all drug entities relevant to answering the question. For each identified drug entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: drug
   - Entity Description: A summary of the specific drug related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include drug category, chemical composition, indications, mechanisms of action, dosage forms, routes of administration, dosage and usage instructions, side effects and adverse reactions, contraindications and precautions, clinical research, market information, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What are common antidepressant drugs?
Input Text:
Antidepressant drugs are commonly used to treat depression. Common examples include sertraline, fluoxetine, and duloxetine. These drugs work by regulating neurotransmitters in the brain to improve mood. Common side effects of sertraline include headaches, insomnia, and sexual dysfunction; fluoxetine may cause decreased appetite, anxiety, and insomnia; duloxetine may lead to nausea, dry mouth, and constipation.

################
Output:
("entity", "sertraline", "drug", "Sertraline is used to treat depression, common side effects include headaches, insomnia, and sexual dysfunction")；
("entity", "fluoxetine", "drug", "Fluoxetine is used to treat depression, may cause decreased appetite, anxiety, and insomnia")；
("entity", "duloxetine", "drug", "Duloxetine is used to treat depression, may cause nausea, dry mouth, and constipation")；
("entity", "antidepressant drugs", "drug category", "Antidepressant drugs are used to treat depression by regulating neurotransmitters to improve mood")；
#############################

Step6.-technique_entity_extraction-
Identify all technique entities relevant to answering the question. For each identified technique entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: technique
   - Entity Description: A summary of the specific technique related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include technique name, category, background and development history, basic principles, application areas, innovations and features, advantages and challenges, current status and trends, market and economic impact, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What are the applications of artificial intelligence technology?
Input Text:
Artificial intelligence (AI) is a technology that simulates human intelligence, capable of performing complex tasks such as speech recognition, image recognition, natural language processing, and machine learning. AI technology has been widely applied in various fields, including healthcare, finance, education, transportation, and more. For example, in healthcare, AI can be used for disease diagnosis, medical image analysis, and personalized treatment.

################
Output:
("entity", "artificial intelligence", "technique", "Artificial intelligence is widely applied in healthcare, finance, education, transportation, and entertainment")；
("entity", "speech recognition", "technique", "Artificial intelligence can perform speech recognition")；
("entity", "image recognition", "technique", "Artificial intelligence can perform image recognition, such as medical image analysis and automatic labeling")；
("entity", "natural language processing", "technique", "Artificial intelligence can perform natural language processing")；
("entity", "machine learning", "technique", "Machine learning is a method within artificial intelligence")；
#############################

Step7.-number_entity_extraction-
Identify all numerical entities relevant to answering the question. For each identified entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: number.
   - Entity Description: The relevance of the number to the specific event, activity, or context in the material. Based on the material, provide the most relevant description for answering the question. This could include the significance of the number, its role in policy, economy, society, etc., and its impact on event development.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Which indicators or data from China’s economic operation in April 2023 reflect its growth or decline trend?
Input text:
The State Council Information Office held a press conference on China’s import and export situation in the first quarter of 2023 (released on April 13, 2023). According to customs statistics, the total value of China’s goods trade in the first quarter was 9.89 trillion yuan, a year-on-year increase of 4.8%. Exports were 5.65 trillion yuan, up by 8.4%, and imports were 4.24 trillion yuan, up by 0.2%. Detailed analysis shows six main characteristics: First, the import-export growth rate increased month by month. In January 2023, due to the Spring Festival holiday, imports and exports decreased by 7%. In February, the growth rate turned positive, with an 8% increase. In March, the year-on-year growth rate increased to 15.5%, showing a positive trend.
################
Output:
("Entity", "9.89 trillion yuan", "number", "The total value of China’s goods trade in the first quarter of 2023 was 9.89 trillion yuan.");
("Entity", "4.8%", "number", "China’s import and export trade in the first quarter of 2023 increased by 4.8% year-on-year.");
("Entity", "5.65 trillion yuan", "number", "China’s export total in the first quarter of 2023 was 5.65 trillion yuan.");
("Entity", "8.4%", "number", "China’s export increased by 8.4% year-on-year in the first quarter of 2023.");
("Entity", "4.24 trillion yuan", "number", "China’s import total in the first quarter of 2023 was 4.24 trillion yuan.");
("Entity", "0.2%", "number", "China’s import increased by 0.2% year-on-year in the first quarter of 2023.");
("Entity", "45.7 million", "number", "China had 45.7 million foreign trade enterprises in the first quarter of 2023.");
("Entity", "5.9%", "number", "The number of foreign trade enterprises in China increased by 5.9% year-on-year in the first quarter of 2023.");
("Entity", "7%", "number", "China’s imports and exports decreased by 7% in January 2023 due to the Spring Festival.");
("Entity", "8%", "number", "China’s imports and exports increased by 8% in February 2023.");
("Entity", "15.5%", "number", "China’s import and export growth rate increased to 15.5% year-on-year in March 2023.");
("Entity", "2.6 percentage points", "number", "China’s overall trade growth in the first quarter of 2023 accelerated by 2.6 percentage points compared to the last quarter of 2022.");

#############################

Step8.-device_entity_extraction-
Identify all device entities relevant to answering the question. For each identified device entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: device
   - Entity Description: A summary of the specific device related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include device type, functions, operating principles, manufacturer or brand, design and structure, applicable fields, advantages and features, usage methods, price and market information, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What are common smart home devices?
Input Text:
Smart home devices are connected through the internet and can be remotely controlled and automated. Common smart home devices include smart light bulbs, smart speakers, smart locks, and smart thermostats. For instance, smart light bulbs can adjust brightness and color through a mobile app, smart speakers can play music and control other smart devices, and smart locks offer fingerprint recognition or remote unlocking features.

################
Output:
("entity", "smart light bulb", "device", "Smart light bulbs can adjust brightness and color via a mobile app")；
("entity", "smart speaker", "device", "Smart speakers can play music and control other smart home devices")；
("entity", "smart lock", "device", "Smart locks offer fingerprint recognition or remote unlocking features")；
("entity", "smart thermostat", "device", "Smart thermostats are common smart home devices")；
#############################

Step9.-operation_entity_extraction-
Identify all operation entities relevant to answering the question. For each identified operation entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: operation
   - Entity Description: A summary of the specific operation related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include operation purpose, target, steps, methods, tools or platforms, time and frequency, impact and consequences, permissions or restrictions, examples, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: How do I update the Windows system?
Input Text:
Windows operating system releases new feature updates, and users can manually update by clicking the "Settings" button, going to "Update & Security," and selecting "Check for Updates." During the update process, the device may need to restart, but users can delay the restart if needed.

################
Output:
("entity", "click 'Settings' button", "operation", "By clicking the 'Settings' button, users can access the update options")；
("entity", "go to 'Update & Security'", "operation", "Go to 'Update & Security' to find update-related operations")；
("entity", "check for updates", "operation", "By clicking 'Check for Updates,' users can manually initiate the update process")；
("entity", "restart device", "operation", "During the update, the device may need to restart to complete some actions")；
#############################

Step10. Return all the entities identified in the above steps as a single list, but do not show the extraction details of each step. Only output the final integrated list of entities, separated by semicolons.

Step11. When completed, only output the final integrated list of entities without showing the details of each step. End with the completion delimiter <|COMPLETE|>.

-Real Data-
######################
instruction: {instruction}
Don't response the instruction.
Here is the extraction:
"""
PROMPTS["Legal"] = """-Goal-
Given a instruction which contain a question and relevant reference, and a list of entity types ['person', 'organization', 'location', 'event', 'time', 'number', 'contract', 'clause', 'judgment'], the task is to extract each type of entity step by step, and finally compile a complete list of entities. The extraction process for each entity type must strictly follow the corresponding extraction rules to identify all relevant entities in the documents that will significantly help answer the question. The output format must strictly follow the example, without any additional text or output in other formats like ```json. Additionally, do not output the details of entity extraction for each step, only the final list of entities.
- Steps -

Step1.-person_entity_extraction-
Identify all person entities relevant to answering the question. For each identified person entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: person.
   - Entity Description: A summary of the information related to the specific person in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. Optionally, include other relevant information such as the person's identity, position, major life events, significant achievements or awards, involvement in important historical events, published works, contributions, and relationships.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Where will President Xi Jinping's Latin American trip visit?
Input text:
At the invitation of Peruvian President Boluarte and Brazilian President Lula, Chinese President Xi Jinping will visit Peru from November 13 to 21 to attend the 31st APEC leaders' informal meeting and conduct a state visit to Peru. He will also visit Brazil to attend the 19th G20 summit and conduct a state visit. Key highlights of Xi Jinping's Latin American trip include:
Highlight 1: Xi Jinping’s sixth visit to Latin America since 2013.
Highlight 2: The Rio summit of the G20 injects Chinese strength into global governance.
Highlight 3: Xi's visit to Peru after 8 years aims to further promote China-Peru strategic partnership.
Highlight 4: Xi’s visit to Brazil after 5 years will usher in the next "Golden Fifty Years" of China-Brazil relations.

################
Output:
("Entity", "Boluarte", "person", "Peruvian President Boluarte invited Chinese President Xi Jinping to Peru to attend the APEC meeting.");
("Entity", "Lula", "person", "Brazilian President Lula invited Xi Jinping to Brazil for the G20 summit.");
("Entity", "Xi Jinping", "person", "Chinese President Xi Jinping is about to visit Peru and Brazil for meetings.");

#############################

Step2.-organization_entity_extraction-
Identify all organizations relevant to answering the question. Note that the identified organizations should not include person entities! For each identified organization, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: organization.
   - Entity Description: A summary of the information related to the specific organization in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. For example, the extracted entity description may include the organization's name, function, goals, leadership, historical background, culture, and its role or influence in the related events. For corporate organizations, in addition to extracting the company name and function, also focus on financial data, market share, annual revenue, number of employees, and other numerical information.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What are the largest technology companies in the world in 2023?
Input text:
In 2023, Apple ranked as the largest technology company globally, with annual revenue exceeding $300 billion, followed by Microsoft and Amazon, with annual revenues of about $200 billion and $150 billion, respectively. Google and Meta also hold significant positions in the market, with annual revenues of $180 billion and $120 billion, respectively.

################
Output:
("Entity", "Apple", "organization", "Apple is the largest technology company globally, with annual revenue exceeding $300 billion in 2023.");
("Entity", "Microsoft", "organization", "Microsoft is the second-largest technology company globally, with annual revenue of about $200 billion in 2023.");
("Entity", "Amazon", "organization", "Amazon is the third-largest technology company globally, with annual revenue of about $150 billion in 2023.");
("Entity", "Google", "organization", "Google is a globally renowned technology company, with annual revenue of about $180 billion in 2023.");
("Entity", "Meta", "organization", "Meta has annual revenue of about $120 billion in 2023 and holds significant influence in social media and technology.");

#############################

Step3.-location_entity_extraction-
Identify all location entities relevant to answering the question. For each identified location entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: location.
   - Entity Description: A summary of the information related to the specific location in the context of the question. Only extract the entity descriptions that significantly help answer the question. Optionally, include basic information about the location, its historical background, significant past events, or upcoming major events.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What are the host cities for the 2023 FIFA World Cup?
Input text:
The 2023 FIFA World Cup will be held in Qatar. This is Qatar’s first time hosting the World Cup, and matches will be held in multiple cities, including Doha, Lusail, Al Wakrah, Al Khor, and Umm Salal. The Qatari government has invested heavily in this event, striving to provide world-class facilities and services. Despite some controversies, Qatar is actively preparing for a smooth event.

################
Output:
("Entity", "Qatar", "location", "Qatar is the host country for the 2023 FIFA World Cup.");
("Entity", "Doha", "location", "Doha is the capital of Qatar and one of the host cities for the World Cup.");
("Entity", "Lusail", "location", "Lusail is an important city in Qatar that will host World Cup matches.");
("Entity", "Al Wakrah", "location", "Al Wakrah is a city in Qatar where World Cup matches will take place.");
("Entity", "Al Khor", "location", "Al Khor is a city in Qatar that will host World Cup matches.");
("Entity", "Umm Salal", "location", "Umm Salal is a city in Qatar where World Cup matches will be held.");

#############################

Step4.-event_entity_extraction-
Identify all event entities relevant to answering the question. For each identified event entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: event.
   - Entity Description: Detailed information about the event and its relevance to the question. Based on the information, provide the most relevant and helpful description for answering the question. This can include the background of the event, its time, location, main participants, key activities, and its impact on related fields, society, economy, or culture.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example:

Question: What economic events in April 2023 impacted foreign trade?
Input text:
The State Council Information Office held a press conference on China's import and export data for Q1 2023 (released on April 13, 2023):
According to customs statistics, China's total goods trade import and export value in the first quarter was 9.89 trillion yuan, a year-on-year increase of 4.8%. Exports were 5.65 trillion yuan, an increase of 8.4%, while imports were 4.24 trillion yuan, an increase of 0.2%. The analysis shows six key features: First, the growth rate of imports and exports improved month by month. In January, due to the Chinese New Year holiday, imports and exports decreased by 7%. February "turned positive," with an 8% increase, and in March, the year-on-year growth rate improved to 15.5%, showing a positive trend. Overall growth for the first quarter was 4.8%, accelerating by 2.6 percentage points compared to Q4 of the previous year, and the year started off smoothly. Second, the number of foreign trade enterprises increased steadily. In the first quarter, China had 457,000 foreign trade enterprises, a 5.9% increase year-on-year.

################
Output:
("Entity", "Press Conference on Q1 2023 Import and Export Data", "event", "Press conference held on April 13, 2023, by the State Council Information Office, announcing China's import and export data for Q1, including total value, growth rate, and key features, providing an analysis of foreign trade trends.");
("Entity", "Impact of the Chinese New Year on Foreign Trade", "event", "In January 2023, due to the Chinese New Year holiday, China's imports and exports decreased by 7%, leading to short-term fluctuations in foreign trade growth for the first quarter.");
("Entity", "Foreign Trade Growth Turned Positive in February 2023", "event", "In February 2023, China's foreign trade turned positive, with an 8% growth, marking an important turning point for foreign trade recovery.");
("Entity", "Foreign Trade Growth Rate Increased to 15.5% in March 2023", "event", "In March 2023, China's import and export growth rate sharply increased to 15.5%, continuing the positive trend in foreign trade.");
#############################

Step5.-time_entity_extraction-
Identify all date and time entities relevant to answering the question. For each identified entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: date and time.
   - Entity Description: A summary of the specific information about the date and time relevant to the question. Based on the information, provide the most relevant and helpful description for answering the question. Include the significance of the date or time point in the context of events or activities.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Where will President Xi Jinping’s Latin American trip visit?
Input text:
At the invitation of Peruvian President Boluarte and Brazilian President Lula, Chinese President Xi Jinping will visit Peru from November 13 to 21 to attend the 31st APEC leaders' informal meeting and conduct a state visit. He will also visit Brazil to attend the 19th G20 summit and conduct a state visit. Key highlights of Xi Jinping's Latin American trip include:
Highlight 1: Xi Jinping’s sixth visit to Latin America since 2013.
Highlight 2: The Rio summit of the G20 injects Chinese strength into global governance.
Highlight 3: Xi's visit to Peru after 8 years aims to further promote China-Peru strategic partnership.
Highlight 4: Xi’s visit to Brazil after 5 years will usher in the next "Golden Fifty Years" of China-Brazil relations.

################
Output:
("Entity", "November 13 to 21", "date and time", "Xi Jinping will visit Peru from November 13 to 21, 2024, to attend the APEC meeting and conduct a state visit.");
("Entity", "2013", "date and time", "Xi Jinping's sixth visit to Latin America since 2013.");
("Entity", "2013", "date and time", "Xi Jinping's first visit to Latin America in 2013 marked an important development in China-Latin America relations.");
("Entity", "5 years", "date and time", "Xi Jinping’s visit to Brazil comes after 5 years.");
("Entity", "8 years", "date and time", "Xi Jinping’s visit to Peru comes after 8 years.");

#############################

Step6.-number_entity_extraction-
Identify all numerical entities relevant to answering the question. For each identified entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: number.
   - Entity Description: The relevance of the number to the specific event, activity, or context in the material. Based on the material, provide the most relevant description for answering the question. This could include the significance of the number, its role in policy, economy, society, etc., and its impact on event development.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Which indicators or data from China’s economic operation in April 2023 reflect its growth or decline trend?
Input text:
The State Council Information Office held a press conference on China’s import and export situation in the first quarter of 2023 (released on April 13, 2023). According to customs statistics, the total value of China’s goods trade in the first quarter was 9.89 trillion yuan, a year-on-year increase of 4.8%. Exports were 5.65 trillion yuan, up by 8.4%, and imports were 4.24 trillion yuan, up by 0.2%. Detailed analysis shows six main characteristics: First, the import-export growth rate increased month by month. In January 2023, due to the Spring Festival holiday, imports and exports decreased by 7%. In February, the growth rate turned positive, with an 8% increase. In March, the year-on-year growth rate increased to 15.5%, showing a positive trend.
################
Output:
("Entity", "9.89 trillion yuan", "number", "The total value of China’s goods trade in the first quarter of 2023 was 9.89 trillion yuan.");
("Entity", "4.8%", "number", "China’s import and export trade in the first quarter of 2023 increased by 4.8% year-on-year.");
("Entity", "5.65 trillion yuan", "number", "China’s export total in the first quarter of 2023 was 5.65 trillion yuan.");
("Entity", "8.4%", "number", "China’s export increased by 8.4% year-on-year in the first quarter of 2023.");
("Entity", "4.24 trillion yuan", "number", "China’s import total in the first quarter of 2023 was 4.24 trillion yuan.");
("Entity", "0.2%", "number", "China’s import increased by 0.2% year-on-year in the first quarter of 2023.");
("Entity", "45.7 million", "number", "China had 45.7 million foreign trade enterprises in the first quarter of 2023.");
("Entity", "5.9%", "number", "The number of foreign trade enterprises in China increased by 5.9% year-on-year in the first quarter of 2023.");
("Entity", "7%", "number", "China’s imports and exports decreased by 7% in January 2023 due to the Spring Festival.");
("Entity", "8%", "number", "China’s imports and exports increased by 8% in February 2023.");
("Entity", "15.5%", "number", "China’s import and export growth rate increased to 15.5% year-on-year in March 2023.");
("Entity", "2.6 percentage points", "number", "China’s overall trade growth in the first quarter of 2023 accelerated by 2.6 percentage points compared to the last quarter of 2022.");

#############################

Step7.-contract_entity_extraction-
Identify all contract-related entities relevant to answering the question. For each identified contract entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: contract
   - Entity Description: A summary of the specific contract related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include contract name, contract description, parties involved, signing time, signing location, terms and conditions, contract amount, duration, performance location, nature of the contract, attachments or supplementary agreements, performance status, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What contracts has Company A signed with suppliers?
Input Text:
Company A has signed the "Product Procurement Contract" with Supplier B, which outlines the terms of product purchase, payment methods, and delivery times. Additionally, the company has signed the "Technical Cooperation Agreement" with Supplier B, which defines the collaborative content and responsibility allocation in technology research and development. The company ensures that every contract clause is clear and legal to ensure smooth contract performance.

################
Output:
("entity", "Product Procurement Contract", "contract", "Outlines the terms of product purchase, payment methods, and delivery times")；
("entity", "Technical Cooperation Agreement", "contract", "Defines the collaboration and responsibility allocation in technology research and development")；
#############################

Step8.-clause_entity_extraction-
Identify all legal clause entities relevant to answering the question. For each identified legal clause entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: legal clause
   - Entity Description: A summary of the specific legal clause related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include clause name, scope of application, specific content, validity period, other supplementary clauses, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What common legal clauses are found in contracts?
Input Text:
Common legal clauses in contracts include "Breach of Contract Clause", "Dispute Resolution Clause", and "Confidentiality Clause". The "Breach of Contract Clause" outlines the compensation responsibilities if one party fails to fulfill its obligations. The "Dispute Resolution Clause" specifies how disputes should be resolved. The "Confidentiality Clause" ensures that any commercial information obtained during the cooperation is kept confidential.
################
Output:
("entity", "Breach of Contract Clause", "legal clause", "The Breach of Contract Clause outlines the compensation responsibilities for failing to fulfill contract obligations")；
("entity", "Dispute Resolution Clause", "legal clause", "The Dispute Resolution Clause specifies how disputes will be resolved")；
("entity", "Confidentiality Clause", "legal clause", "The Confidentiality Clause ensures the confidentiality of commercial information obtained during cooperation")；
#############################

Step9.-judgment_entity_extraction-
Identify all judgment-related entities relevant to answering the question. For each identified judgment entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: judgment
   - Entity Description: A summary of the specific judgment related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include judgment name or case number, court, judgment date, case type, judgment result, case background, legal basis, execution status, appeal status, and other related clauses or additional requirements.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What was the result of the judgment (2024) Hu Min Chu 456?
Input Text:
On July 15, 2024, the Shanghai People's Court made the judgment (2024) Hu Min Chu 456, involving a dispute over intellectual property infringement. The court ruled that the defendant used the plaintiff's patented technology without authorization, constituting patent infringement. The defendant was ordered to cease the infringement and pay the plaintiff compensation of 2 million RMB. The defendant's defense was rejected, and the court dismissed its appeal.
################
Output:
("entity", "(2024) Hu Min Chu 456 Judgment", "judgment", "The judgment requires the defendant to cease infringement and pay compensation of 2 million RMB")；
#############################

Step10. Return all the entities identified in the above steps as a single list, but do not show the extraction details of each step. Only output the final integrated list of entities, separated by semicolons.

Step11. When completed, only output the final integrated list of entities without showing the details of each step. End with the completion delimiter <|COMPLETE|>.
-Real Data-
######################
instruction: {instruction}
Don't response the instruction.
Here is the extraction:
"""
PROMPTS["News"] = """-Goal-
给定包含问题和相关资料的指令，和一个实体类型列表['person', 'organization', 'location', 'event', 'time', 'number', 'product', 'policy']，要求在每一步中，完成一类实体的抽取，最后整理得到完整的实体列表。每一类实体的抽取过程需要严格按照对应的抽取规则，从资料中识别所有与问题相关的，对问题回答有明显帮助的该类实体。输出格式严格按照示例，不允许输出其他文字，不允许出现```json。
- 步骤 -
  
Step1.-person_entity_extraction-
识别所有与回答该问题相关的人物实体。对于每个识别出的人物实体，提取以下信息：

   - 实体名称：实体的名称
   - 实体类型：人物
   - 实体描述：资料中特定人物与所提问题相关的信息概要。根据资料，对该实体进行最切合问题、最有助于问题回答的描述。可以选择性的包含该人物的身份、职务、重要的生平事件、重大成就或奖项、参与的重要历史事件、发布的作品或重要的贡献以及人际关系等其他相关信息。
   - 每个实体的格式为 ("实体",<实体名称>,<实体类型>,<实体描述>)。
     ######################
- 示例 -
  ######################
  示例1：

问题：习近平主席的拉美之行将前往哪些地方？
输入文本：
应秘鲁总统博鲁阿尔特、巴西总统卢拉邀请，中国国家主席习近平将于11月13日至21日赴秘鲁出席亚太经合组织第三十一次领导人非正式会议并对秘鲁进行国事访问、赴巴西出席二十国集团领导人第十九次峰会并对巴西进行国事访问。习近平主席拉美之行，这些看点值得关注。
看点一：2013年以来习近平主席第六次到访拉美。
看点二：二十国集团里约峰会为完善全球治理注入中国力量。
看点三：时隔8年再次访问秘鲁，推动中秘全面战略伙伴关系取得更多积极成果。
看点四：时隔5年再次访问巴西，携手开启中巴关系下一个“黄金五十年”。

################
输出:
("实体"，"博鲁阿尔特"，"人物"，"秘鲁总统博鲁阿尔特邀请中国国家主席习近平赴秘鲁出席亚太经合组织会议")；
("实体"，"卢拉"，"人物"，"巴西总统卢拉邀请习近平赴巴西参加G20峰会")；
("实体"，"习近平"，"人物"，"中国国家主席习近平即将前往秘鲁和巴西参加会议")；
#############################


Step2.-organization_entity_extraction-
识别所有与回答该问题相关的组织。注意，识别的组织不要包括人物实体！对于每个识别出的组织，提取以下信息：

   - 实体名称：实体的名称
   - 实体类型：组织
   - 实体描述：资料中特定组织与所提问题相关的信息概要。根据资料，对该实体进行最切合问题、最有助于问题回答的描述。比如，提取的实体描述可能是该组织的名称、职能、目标、领导、历史背景、文化、在相关事件中的作用或影响力。对于公司类组织，除了提取公司名称和职能外，还需要关注公司的财务数据、市场份额、年收入、员工人数等数值信息。
   - 每个实体的格式为 ("实体"，<实体名称>，<实体类型>，<实体描述>)。

######################

- 示例 -
  ######################
  示例1：

问题：2023年全球最大的科技公司有哪些？
输入文本：
在2023年，苹果公司以超过3000亿美元的年收入位居全球科技公司之首，随后是微软和亚马逊，分别年收入约为2000亿美元和1500亿美元。谷歌和Meta也在市场中占有重要地位，年收入分别为1800亿美元和1200亿美元。

################

输出：
("实体"，"苹果公司"，"组织"，"苹果公司是全球最大的科技公司，2023年年收入超过3000亿美元。")；
("实体"，"微软"，"组织"，"微软是全球第二大科技公司，2023年年收入约为2000亿美元。")；
("实体"，"亚马逊"，"组织"，"亚马逊是全球第三大科技公司，2023年年收入约为1500亿美元。")；
("实体"，"谷歌"，"组织"，"谷歌在2023年的年收入约为1800亿美元，是全球知名的科技公司。")；
("实体"，"Meta"，"组织"，"Meta在2023年的年收入约为1200亿美元，在社交媒体和技术领域具有重要影响力。")；
#############################


Step3.-location_entity_extraction-
识别所有与回答该问题相关的地点实体。对于每个识别出的地点实体，提取以下信息：

   - 实体名称：实体的名称
   - 实体类型：地点
   - 实体描述：资料中特定地点与所提问题相关的信息概要。只提取对回答该问题有显著帮助的实体描述。可以选择性的包含该地点的基本信息、历史背景、发生过的重要事件或即将发生的重要事件。
   - 每个实体的格式为 ("实体"，<实体名称>，<实体类型>，<实体描述>)。

######################

- 示例 -
  ######################
  示例1：

问题：2023年世界杯足球赛的举办城市有哪些？
输入文本：
2023年国际足联世界杯将在卡塔尔举办。这是卡塔尔首次承办世界杯赛事，比赛将在多个城市进行，包括多哈、卢塞尔、阿尔瓦克拉、艾尔科尔和乌姆萨拉尔。卡塔尔政府为此次赛事投入了大量资金，力求提供世界一流的设施和服务。尽管面临一些争议，卡塔尔依然积极准备，力求赛事顺利进行。

################
输出:
("实体"，"卡塔尔"，"地点"，"卡塔尔是2023年国际足联世界杯的主办国")；
("实体"，"多哈"，"地点"，"多哈是卡塔尔的首都，也是世界杯举办城市之一")；
("实体"，"卢塞尔"，"地点"，"卢塞尔是卡塔尔的重要城市之一，将举办世界杯赛事")；
("实体"，"阿尔瓦克拉"，"地点"，"阿尔瓦克拉是卡塔尔的一座城市，世界杯比赛将在此进行")；
("实体"，"艾尔科尔"，"地点"，"艾尔科尔是卡塔尔的城市之一，将承办世界杯赛事")；
("实体"，"乌姆萨拉尔"，"地点"，"乌姆萨拉尔是卡塔尔的城市之一，世界杯比赛将在此进行")；
#############################


Step4.-event_entity_extraction-
识别所有与回答该问题相关的事件实体。对于每个识别出的事件实体，提取以下信息：

   - 实体名称：实体的名称
   - 实体类型：事件
   - 实体描述：资料中该事件与所提问题相关的详细信息。根据资料，对该实体进行最切合问题、最有助于问题回答的描述。可以描述该事件的背景、发生的时间、地点、主要参与者、关键活动及其对相关领域、社会、经济或文化的影响。
   - 每个实体的格式为 ("实体",<实体名称>,<实体类型>,<实体描述>)。
     ######################
- 示例 -
  ######################
  示例：
  问题： 2023年4月份有哪些经济相关的事件对外贸情况产生影响？
  输入文本：
  国务院新闻办就2023年一季度进出口情况举行发布会（发布于2023年4月13日）：
  据海关统计，一季度我国货物贸易进出口总值9.89万亿元人民币，同比增长4.8%。其中，出口5.65万亿元，同比增长8.4%；进口4.24万亿元，同比增长0.2%。具体分析，主要有以下六个方面的特点：一是进出口增速逐月提升。今年1月份，受春节假期影响，进出口下降7%。2月“由负转正”，当月增长8%，3月同比增速提升到15.5%，呈现逐月向好态势。一季度整体增长4.8%，较去年四季度提速2.6个百分点，开局平稳向好。二是外贸经营主体数量稳中有增。一季度，我国有进出口实绩外贸企业45.7万家，同比增长5.9%。

################
输出：
("实体"，"2023年一季度进出口情况发布会"，"事件"，"2023年4月13日国务院新闻办举行的发布会，公布了一季度我国货物贸易进出口数据，包括总值、增长率以及主要特点，对外贸走势提供分析")；
("实体"，"春节假期对外贸的影响"，"事件"，"2023年1月，因春节假期导致我国进出口下降7%，对一季度外贸整体增长带来短期波动")；
("实体"，"2023年2月外贸增长转正"，"事件"，"2023年2月我国外贸进出口由负转正，当月增长8%，成为外贸回升的重要节点")；
("实体"，"2023年3月外贸增速提升至15.5%", "事件", "2023年3月我国进出口同比增速大幅提升至15.5%，延续外贸向好的趋势")；
#############################


Step5.-time_entity_extraction-
识别所有与回答该问题相关的日期和时间实体。对于每个识别出的实体，提取以下信息：

   - 实体名称：实体的名称
   - 实体类型：日期和时间
   - 实体描述：资料中与所提问题相关的日期和时间的具体信息概要。根据资料，对该实体进行最切合问题、最有助于问题回答的描述。包括该日期或时间点在事件、活动中的重要性。
   - 每个实体的格式为 ("实体"，<实体名称>，<实体类型>，<实体描述>)。
     ######################
- 示例 -
  ######################
  示例1：

问题：习近平主席的拉美之行将前往哪些地方？
输入文本：
应秘鲁总统博鲁阿尔特、巴西总统卢拉邀请，中国国家主席习近平将于11月13日至21日赴秘鲁出席亚太经合组织第三十一次领导人非正式会议并对秘鲁进行国事访问、赴巴西出席二十国集团领导人第十九次峰会并对巴西进行国事访问。习近平主席拉美之行，这些看点值得关注。
看点一：2013年以来习近平主席第六次到访拉美。
看点二：二十国集团里约峰会为完善全球治理注入中国力量。
看点三：时隔8年再次访问秘鲁，推动中秘全面战略伙伴关系取得更多积极成果。
看点四：时隔5年再次访问巴西，携手开启中巴关系下一个“黄金五十年”。

################
输出:
("实体"，"11月13日至21日"，"日期和时间"，"习近平主席将于2024年11月13日至21日赴秘鲁出席亚太经合组织会议并进行国事访问")；
("实体"，"2013年"，"日期和时间"，"习近平主席自2013年以来第六次访问拉美")；
("实体"，"2013年", "日期和时间", "习近平主席2013年首次访问拉美，标志着中拉关系的重要发展")；
("实体"，"5年", "日期和时间", "习近平主席时隔5年再次访问巴西")；
("实体"，"8年", "日期和时间", "习近平主席时隔8年再次访问秘鲁")；
#############################


Step6.-number_entity_extraction-
识别所有与回答该问题相关的数值实体。对于每个识别出的实体，提取以下信息：

   - 实体名称：实体的名称
   - 实体类型：数值
   - 实体描述：资料中与所提问题相关的数值与具体事件、活动或情境的相关性。根据资料，对该实体进行最切合问题、最有助于问题回答的描述。可以包括具体的数值意义、它在政策、经济、社会等方面的作用，及其对事件发展的影响。
   - 每个实体的格式为 ("实体"，<实体名称>，<实体类型>，<实体描述>)。
     ######################
- 示例 -
  ######################
  示例1：

问题：2023年4月份中国经济运行中哪些指标或数据体现了其增长或下降趋势？
输入文本：
国务院新闻办就2023年一季度进出口情况举行发布会（发布于2023年4月13日）：据海关统计，一季度我国货物贸易进出口总值9.89万亿元人民币，同比增长4.8%。其中，出口5.65万亿元，同比增长8.4%；进口4.24万亿元，同比增长0.2%。具体分析，主要有以下六个方面的特点：一是进出口增速逐月提升。今年1月份，受春节假期影响，进出口下降7%。2月“由负转正”，当月增长8%，3月同比增速提升到15.5%，呈现逐月向好态势。一季度整体增长4.8%，较去年四季度提速2.6个百分点，开局平稳向好。二是外贸经营主体数量稳中有增。一季度，我国有进出口实绩外贸企业45.7万家，同比增长5.9%。

################
输出:
("实体"，"9.89万亿元人民币"，"数值"，"2023年一季度我国货物贸易进出口总值为9.89万亿元人民币")；
("实体"，"4.8%"，"数值"，"2023年一季度我国货物贸易进出口同比增长4.8%")；
("实体"，"5.65万亿元人民币"，"数值"，"2023年一季度我国出口总值为5.65万亿元人民币")；
("实体"，"8.4%"，"数值"，"2023年一季度我国出口同比增长8.4%")；
("实体"，"4.24万亿元人民币"，"数值"，"2023年一季度我国进口总值为4.24万亿元人民币")；
("实体"，"0.2%"，"数值"，"2023年一季度我国进口同比增长0.2%")；
("实体"，"45.7万家"，"数值"，"2023年一季度我国有45.7万家外贸企业")；
("实体"，"5.9%"，"数值"，"2023年一季度我国外贸企业数量同比增长5.9%")；
("实体"，"7%"，"数值"，"2023年1月我国进出口下降7%")；
("实体"，"8%"，"数值"，"2023年2月我国进出口增长8%")；
("实体"，"15.5%"，"数值"，"2023年3月我国进出口同比增速提升到15.5%")；
("实体"，"2.6个百分点"，"数值"，"2023年一季度整体增长较去年四季度提速2.6个百分点")；
#############################

Step7.-product_entity_extraction-
识别所有与回答该问题相关的产品实体。注意：产品实体被定义为具有商业性质的具体物品或服务，包括但不限于消费品、电子产品、软件、工具、车辆等。会议、活动或其他非物质类实体不应被视为产品实体。
  对于每个识别出的产品实体，提取以下信息：

   - 实体名称：实体的名称
   - 实体类型：产品
   - 实体描述：资料中特定产品与所提问题相关的信息概要。比如，提取的实体描述可能是该产品的功能、市场定位、目标用户群体、技术规格、价格、发布背景以及该产品在市场中的表现或对消费者的影响。
   - 每个实体的格式为 ("实体"，<实体名称>，<实体类型>，<实体描述>)。
     ######################
- 示例 -
  ######################
  示例1：

问题：2023年有哪些热门智能手机？
输入文本：
苹果公司在2023年推出了iPhone 14，配备A16芯片和改进的相机系统，市场定位高端，售价约为999美元。三星的Galaxy S23系列也在2023年发布，主打强大的摄影功能和高刷新率显示屏，售价在799美元到1199美元之间。小米的13 Pro凭借其性价比和强大的性能受到了消费者的青睐，售价约为749美元。
################

输出：
("实体"，"iPhone 14"，"产品"，"iPhone 14是苹果公司在2023年推出的智能手机，配备A16芯片和改进的相机系统，市场定位高端")；
("实体"，"Galaxy S23"，"产品"，"Galaxy S23是三星在2023年发布的智能手机，主打强大的摄影功能和高刷新率显示屏")；
("实体"，"小米13 Pro"，"产品"，"小米13 Pro凭借其性价比和强大的性能在2023年受到了消费者的青睐")；
#############################


Step8.-policy_entity_extraction-
识别所有与回答该问题相关的政策实体。对于每个识别出的政策实体，提取以下信息：

   - 实体名称：实体的名称
   - 实体类型：政策
   - 实体描述：资料中政策与所提问题相关的信息概要。根据资料的真实情况，可以描述该政策的目标、实施背景、主要措施、预期效果、政策受益者、发布主体等，特别是政策与经济、社会、技术等方面的关系。
   - 每个实体的格式为 ("实体"，<实体名称>，<实体类型>，<实体描述>)。
     ######################
- 示例 -
  ######################
  示例1：

问题：美国政府在2023年发布了哪些重要的经济政策？
输入文本：
2023年，美国政府宣布了几项关键的经济政策。首先，拜登政府推出了“美国就业计划”，旨在推动基础设施建设、创造就业机会。其次，政府实施了“绿色能源投资政策”，通过税收减免和补贴措施，鼓励企业和家庭投资清洁能源。第三，“基建振兴法案”被重启，以加速基础设施的现代化，预计将投入超过1万亿美元。其中，“美国就业计划”侧重于通过建设道路、桥梁、宽带等基础设施来提升经济增长潜力，重点扶持制造业、建筑业等行业的就业机会。“绿色能源投资政策”则鼓励可再生能源项目，旨在减少碳排放并实现2030年能源转型目标。“基建振兴法案”则力求加快老化基础设施的更新，提升国家竞争力。

################ 
输出：
("实体"，"美国就业计划"，"政策"，"拜登政府推出的“美国就业计划”旨在通过基础设施建设和制造业振兴，推动经济增长并创造就业机会")；
("实体"，"绿色能源投资政策"，"政策"，"美国政府实施的“绿色能源投资政策”，通过税收减免和补贴措施，鼓励企业和家庭投资清洁能源项目")；
("实体"，"基建振兴法案"，"政策"，"美国政府重启的“基建振兴法案”，投资超过1万亿美元，加速基础设施现代化，提升国家竞争力")；
#############################


Step9.以单一列表形式返回上述全部步骤中识别的所有实体的输出,不要输出每一步的实体抽取细节。使用分号作为列表分隔符。

Step10.完成时，只输出最后整合的整体实体列表，不用输出每一步的，最后输出完成分隔符<|COMPLETE|>。
-Real Data-
######################
指令: {instruction}
不要输出指令，只输出实体列表
这是抽取的实体列表：

"""

PROMPTS["bio_medical_research"] = ["person", "organism", "symptom", "disease", "drug", "technique", "number", "device", "operation"]
PROMPTS["general_knowledge"] = ["person", "organism", "organization", "location", "event", "time", "diet", "number", "product"]
PROMPTS["legal_contracts"] = ["person", "organization", "location", "event", "time", "number", "contract", "clause", "judgment"]
PROMPTS["customer_support"] = ["person", "technique", "operation", "event", "time", "number", "device", "product"]
PROMPTS["finance"] = ["person", "organization", "event", "time", "number", "operation", "product", "policy"]
PROMPTS["news"] = ["person", "organization", "location", "event", "time", "number", "product", "policy"]


PROMPTS["intention"] = """-Goal-
Given a question and a set of documents, classify the question into one of the predefined domains in {domain} by evaluating the content of the question and its relevance to the provided documents. The classification should be based on the primary focus of the question (e.g., medical, legal, financial) and the domain context found in the documents. Ensure that the answer is based on a careful assessment of the subject matter, keywords, and overall context of both the question and the document(s).
!!The output can only contain one domain of the problem, do not output the cause and other information!!
######################
-Examples-
######################

Example 1:
domain: [bio_medical_research, general_knowledge, legal_contracts, customer_support, finance, news]
question:
Is there a functional neural correlate of individual differences in cardiovascular reactivity?
document:
[ "The present study tested whether individuals who differ in the magnitude of their blood pressure reactions to a behavioral stressor also differ in their stressor-induced patterns of functional neural activation.", "This study examined whether heightened cardiovascular reactivity and low socioeconomic status had synergistic effects on the progression of carotid atherosclerosis in a population of eastern Finnish men.", "Heart rate variability (HRV), a measure of autonomic function, has been associated with cognitive function, but studies are conflicting. Previous studies have also not controlled for familial and genetic influences.", "Low socioeconomic status is associated with increased cardiovascular disease risk. We hypothesized that psychobiological pathways, specifically slow recovery in blood pressure and heart rate variability following mental stress, partly mediate social inequalities in risk.", "Does background stress heighten or dampen children's cardiovascular responses to acute stress?" ]
################
Output:
bio_medical_research
#############################

Example 2:
domain: [bio_medical_research, general_knowledge, legal_contracts, customer_support, finance, news]
question:
Which genus of flowering plant is found in an environment further south, Crocosmia or Cimicifuga?
document:
[ "Actaea arizonica is a species of flowering plant in the buttercup family known by the common name Arizona bugbane. It is endemic to Arizona in the United States, where it occurs in Coconino, Gila, and Yavapai Counties. Like some other species in genus \"Actaea\", this plant was formerly included in the genus \"Cimicifuga\".", "Crocosmia paniculata (Aunt Eliza) is a bulbous flowering plant that is native to eastern South Africa, Lesotho, and Swaziland, growing in wet areas by streams, marshes, and drainages. Plants reach 4 to 5 ft (1.2–1.5 m) tall, with lanceolate leaves and deep orange to orange-brown flowers. It is a popular ornamental plant.", "Crocosmia ( ; J. E. Planchon, 1851) (montbretia) is a small genus of flowering plants in the iris family, Iridaceae. It is native to the grasslands of southern and eastern Africa, ranging from South Africa to Sudan. One species is endemic to Madagascar.", "Cimicifuga (bugbane or cohosh) was a genus of between 12-18 species of flowering plants belonging to the family Ranunculaceae, native to temperate regions of the Northern Hemisphere." ]
################
Output:
general_knowledge
#############################

Example 3:
domain: [bio_medical_research, general_knowledge, legal_contracts, customer_support, finance, news]
question:
Describe the key technologies or innovation points of deep integration of artificial intelligence in the field of sports in 2023.
document:
[ "Artificial Intelligence is changing Football, will the human brain finally give way to machine decision-making? (Posted October 31, 2023) :." The professional soccer world is already deeply using various new technologies related to artificial intelligence to analyze various training and competition scenarios and deeply design new sports modes. There is already a growing consensus that an era in which professional sports are ruled by AI may soon be upon us. It is not clear whether the Hollywood movie scenario of robots eventually taking over the world and annihilating humans will happen, but the scenario of AI and these new technologies ruling the world of sports, especially football, may be in sight. A year ago, the British "Times" once reported that their columnist, Tony Cascarino, a former Irish center who is famous for heading, went to a football technology lab and used VR headsets to experience the training of heading in sports football. How Cloud Computing + AI is reshaping Sports Events:. The operation management background is built on the exclusive management platform of the Asian Games nail, which provides online digital office services for the staff, and also provides the possibility for the timely response and processing of the needs of the participants. Ai-powered smart Asian Games applications are not only in the Asian Games Village, but also in the broadcast of events. Alibaba Cloud draws rich experience from the Tokyo Olympic Games and the Beijing Winter Olympics, and applies the experience of cloud broadcasting to the current Asian Games. Cloud computing also makes the broadcasting system more flexible and improves the viewing experience. As the first Asian Games to broadcast on the cloud, this Asian Games broke through the previous traditional satellite broadcast method, broadcast technology to achieve technological innovation, to achieve cloud broadcast, can quickly open the "new highway" for the right to broadcast sports events on demand to bring "all roads lead to Rome" on the cloud broadcast freedom" ]
################
Output:
news
#############################
-Real Data-
######################
domain: {domain}
question: {question}
document: {document}
######################
Output:
"""

PROMPTS["entity_extraction"] = """-Goal-
Given a question, documents, and a list of entity types {entity_type}, the task is to extract each type of entity step by step, and finally compile a complete list of entities. The extraction process for each entity type must strictly follow the corresponding extraction rules to identify all relevant entities in the documents that will significantly help answer the question. The output format must strictly follow the example, without any additional text or output in other formats like ```json. Additionally, do not output the details of entity extraction for each step, only the final list of entities.
- Steps -
"""

PROMPTS["entity_extraction_person"] = """-person_entity_extraction-
Identify all person entities relevant to answering the question. For each identified person entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: person.
   - Entity Description: A summary of the information related to the specific person in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. Optionally, include other relevant information such as the person's identity, position, major life events, significant achievements or awards, involvement in important historical events, published works, contributions, and relationships.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Where will President Xi Jinping's Latin American trip visit?
Input text:
At the invitation of Peruvian President Boluarte and Brazilian President Lula, Chinese President Xi Jinping will visit Peru from November 13 to 21 to attend the 31st APEC leaders' informal meeting and conduct a state visit to Peru. He will also visit Brazil to attend the 19th G20 summit and conduct a state visit. Key highlights of Xi Jinping's Latin American trip include:
Highlight 1: Xi Jinping’s sixth visit to Latin America since 2013.
Highlight 2: The Rio summit of the G20 injects Chinese strength into global governance.
Highlight 3: Xi's visit to Peru after 8 years aims to further promote China-Peru strategic partnership.
Highlight 4: Xi’s visit to Brazil after 5 years will usher in the next "Golden Fifty Years" of China-Brazil relations.

################
Output:
("Entity", "Boluarte", "person", "Peruvian President Boluarte invited Chinese President Xi Jinping to Peru to attend the APEC meeting.");
("Entity", "Lula", "person", "Brazilian President Lula invited Xi Jinping to Brazil for the G20 summit.");
("Entity", "Xi Jinping", "person", "Chinese President Xi Jinping is about to visit Peru and Brazil for meetings.");

#############################
"""
PROMPTS["entity_extraction_organization"] = """-organization_entity_extraction-
Identify all organizations relevant to answering the question. Note that the identified organizations should not include person entities! For each identified organization, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: organization.
   - Entity Description: A summary of the information related to the specific organization in the context of the question. Based on the information, provide the most relevant and helpful description for answering the question. For example, the extracted entity description may include the organization's name, function, goals, leadership, historical background, culture, and its role or influence in the related events. For corporate organizations, in addition to extracting the company name and function, also focus on financial data, market share, annual revenue, number of employees, and other numerical information.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What are the largest technology companies in the world in 2023?
Input text:
In 2023, Apple ranked as the largest technology company globally, with annual revenue exceeding $300 billion, followed by Microsoft and Amazon, with annual revenues of about $200 billion and $150 billion, respectively. Google and Meta also hold significant positions in the market, with annual revenues of $180 billion and $120 billion, respectively.

################
Output:
("Entity", "Apple", "organization", "Apple is the largest technology company globally, with annual revenue exceeding $300 billion in 2023.");
("Entity", "Microsoft", "organization", "Microsoft is the second-largest technology company globally, with annual revenue of about $200 billion in 2023.");
("Entity", "Amazon", "organization", "Amazon is the third-largest technology company globally, with annual revenue of about $150 billion in 2023.");
("Entity", "Google", "organization", "Google is a globally renowned technology company, with annual revenue of about $180 billion in 2023.");
("Entity", "Meta", "organization", "Meta has annual revenue of about $120 billion in 2023 and holds significant influence in social media and technology.");

#############################
"""
PROMPTS["entity_extraction_location"] = """-location_entity_extraction-
Identify all location entities relevant to answering the question. For each identified location entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: location.
   - Entity Description: A summary of the information related to the specific location in the context of the question. Only extract the entity descriptions that significantly help answer the question. Optionally, include basic information about the location, its historical background, significant past events, or upcoming major events.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What are the host cities for the 2023 FIFA World Cup?
Input text:
The 2023 FIFA World Cup will be held in Qatar. This is Qatar’s first time hosting the World Cup, and matches will be held in multiple cities, including Doha, Lusail, Al Wakrah, Al Khor, and Umm Salal. The Qatari government has invested heavily in this event, striving to provide world-class facilities and services. Despite some controversies, Qatar is actively preparing for a smooth event.

################
Output:
("Entity", "Qatar", "location", "Qatar is the host country for the 2023 FIFA World Cup.");
("Entity", "Doha", "location", "Doha is the capital of Qatar and one of the host cities for the World Cup.");
("Entity", "Lusail", "location", "Lusail is an important city in Qatar that will host World Cup matches.");
("Entity", "Al Wakrah", "location", "Al Wakrah is a city in Qatar where World Cup matches will take place.");
("Entity", "Al Khor", "location", "Al Khor is a city in Qatar that will host World Cup matches.");
("Entity", "Umm Salal", "location", "Umm Salal is a city in Qatar where World Cup matches will be held.");

#############################
"""
PROMPTS["entity_extraction_event"] = """-event_entity_extraction-
Identify all event entities relevant to answering the question. For each identified event entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: event.
   - Entity Description: Detailed information about the event and its relevance to the question. Based on the information, provide the most relevant and helpful description for answering the question. This can include the background of the event, its time, location, main participants, key activities, and its impact on related fields, society, economy, or culture.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example:

Question: What economic events in April 2023 impacted foreign trade?
Input text:
The State Council Information Office held a press conference on China's import and export data for Q1 2023 (released on April 13, 2023):
According to customs statistics, China's total goods trade import and export value in the first quarter was 9.89 trillion yuan, a year-on-year increase of 4.8%. Exports were 5.65 trillion yuan, an increase of 8.4%, while imports were 4.24 trillion yuan, an increase of 0.2%. The analysis shows six key features: First, the growth rate of imports and exports improved month by month. In January, due to the Chinese New Year holiday, imports and exports decreased by 7%. February "turned positive," with an 8% increase, and in March, the year-on-year growth rate improved to 15.5%, showing a positive trend. Overall growth for the first quarter was 4.8%, accelerating by 2.6 percentage points compared to Q4 of the previous year, and the year started off smoothly. Second, the number of foreign trade enterprises increased steadily. In the first quarter, China had 457,000 foreign trade enterprises, a 5.9% increase year-on-year.

################
Output:
("Entity", "Press Conference on Q1 2023 Import and Export Data", "event", "Press conference held on April 13, 2023, by the State Council Information Office, announcing China's import and export data for Q1, including total value, growth rate, and key features, providing an analysis of foreign trade trends.");
("Entity", "Impact of the Chinese New Year on Foreign Trade", "event", "In January 2023, due to the Chinese New Year holiday, China's imports and exports decreased by 7%, leading to short-term fluctuations in foreign trade growth for the first quarter.");
("Entity", "Foreign Trade Growth Turned Positive in February 2023", "event", "In February 2023, China's foreign trade turned positive, with an 8% growth, marking an important turning point for foreign trade recovery.");
("Entity", "Foreign Trade Growth Rate Increased to 15.5% in March 2023", "event", "In March 2023, China's import and export growth rate sharply increased to 15.5%, continuing the positive trend in foreign trade.");
#############################
"""
PROMPTS["entity_extraction_time"] = """-time_entity_extraction-
Identify all date and time entities relevant to answering the question. For each identified entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: date and time.
   - Entity Description: A summary of the specific information about the date and time relevant to the question. Based on the information, provide the most relevant and helpful description for answering the question. Include the significance of the date or time point in the context of events or activities.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Where will President Xi Jinping’s Latin American trip visit?
Input text:
At the invitation of Peruvian President Boluarte and Brazilian President Lula, Chinese President Xi Jinping will visit Peru from November 13 to 21 to attend the 31st APEC leaders' informal meeting and conduct a state visit. He will also visit Brazil to attend the 19th G20 summit and conduct a state visit. Key highlights of Xi Jinping's Latin American trip include:
Highlight 1: Xi Jinping’s sixth visit to Latin America since 2013.
Highlight 2: The Rio summit of the G20 injects Chinese strength into global governance.
Highlight 3: Xi's visit to Peru after 8 years aims to further promote China-Peru strategic partnership.
Highlight 4: Xi’s visit to Brazil after 5 years will usher in the next "Golden Fifty Years" of China-Brazil relations.

################
Output:
("Entity", "November 13 to 21", "date and time", "Xi Jinping will visit Peru from November 13 to 21, 2024, to attend the APEC meeting and conduct a state visit.");
("Entity", "2013", "date and time", "Xi Jinping's sixth visit to Latin America since 2013.");
("Entity", "2013", "date and time", "Xi Jinping's first visit to Latin America in 2013 marked an important development in China-Latin America relations.");
("Entity", "5 years", "date and time", "Xi Jinping’s visit to Brazil comes after 5 years.");
("Entity", "8 years", "date and time", "Xi Jinping’s visit to Peru comes after 8 years.");

#############################
"""
PROMPTS["entity_extraction_number"] = """-number_entity_extraction-
Identify all numerical entities relevant to answering the question. For each identified entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: number.
   - Entity Description: The relevance of the number to the specific event, activity, or context in the material. Based on the material, provide the most relevant description for answering the question. This could include the significance of the number, its role in policy, economy, society, etc., and its impact on event development.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: Which indicators or data from China’s economic operation in April 2023 reflect its growth or decline trend?
Input text:
The State Council Information Office held a press conference on China’s import and export situation in the first quarter of 2023 (released on April 13, 2023). According to customs statistics, the total value of China’s goods trade in the first quarter was 9.89 trillion yuan, a year-on-year increase of 4.8%. Exports were 5.65 trillion yuan, up by 8.4%, and imports were 4.24 trillion yuan, up by 0.2%. Detailed analysis shows six main characteristics: First, the import-export growth rate increased month by month. In January 2023, due to the Spring Festival holiday, imports and exports decreased by 7%. In February, the growth rate turned positive, with an 8% increase. In March, the year-on-year growth rate increased to 15.5%, showing a positive trend.
################
Output:
("Entity", "9.89 trillion yuan", "number", "The total value of China’s goods trade in the first quarter of 2023 was 9.89 trillion yuan.");
("Entity", "4.8%", "number", "China’s import and export trade in the first quarter of 2023 increased by 4.8% year-on-year.");
("Entity", "5.65 trillion yuan", "number", "China’s export total in the first quarter of 2023 was 5.65 trillion yuan.");
("Entity", "8.4%", "number", "China’s export increased by 8.4% year-on-year in the first quarter of 2023.");
("Entity", "4.24 trillion yuan", "number", "China’s import total in the first quarter of 2023 was 4.24 trillion yuan.");
("Entity", "0.2%", "number", "China’s import increased by 0.2% year-on-year in the first quarter of 2023.");
("Entity", "45.7 million", "number", "China had 45.7 million foreign trade enterprises in the first quarter of 2023.");
("Entity", "5.9%", "number", "The number of foreign trade enterprises in China increased by 5.9% year-on-year in the first quarter of 2023.");
("Entity", "7%", "number", "China’s imports and exports decreased by 7% in January 2023 due to the Spring Festival.");
("Entity", "8%", "number", "China’s imports and exports increased by 8% in February 2023.");
("Entity", "15.5%", "number", "China’s import and export growth rate increased to 15.5% year-on-year in March 2023.");
("Entity", "2.6 percentage points", "number", "China’s overall trade growth in the first quarter of 2023 accelerated by 2.6 percentage points compared to the last quarter of 2022.");

#############################
"""
PROMPTS["entity_extraction_product"] = """-product_entity_extraction-
Identify all product entities relevant to answering the question. Note: Product entities are defined as specific goods or services with commercial value, including but not limited to consumer goods, electronic products, software, tools, vehicles, etc. Meetings, activities, or other non-material entities should not be considered product entities.
For each identified product entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: product.
   - Entity Description: A summary of the specific product and its relevance to the question. For example, the description might include the product’s functionality, market positioning, target audience, technical specifications, price, release background, and its market performance or consumer impact.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What are the popular smartphones in 2023?
Input text:
Apple launched the iPhone 14 in 2023, equipped with an A16 chip and an upgraded camera system, targeted at the high-end market, with a price of around $999. Samsung’s Galaxy S23 series was also released in 2023, focusing on powerful photography features and a high refresh rate display, priced between $799 and $1199. Xiaomi’s 13 Pro, favored by consumers for its cost-effectiveness and strong performance, is priced at around $749.
################
Output:
("Entity", "iPhone 14", "product", "iPhone 14 is a smartphone released by Apple in 2023, featuring an A16 chip and an upgraded camera system, targeted at the high-end market.");
("Entity", "Galaxy S23", "product", "Galaxy S23 is a smartphone released by Samsung in 2023, focusing on powerful photography features and a high refresh rate display.");
("Entity", "Xiaomi 13 Pro", "product", "Xiaomi 13 Pro is favored by consumers in 2023 for its cost-effectiveness and strong performance.");

#############################
"""
PROMPTS["entity_extraction_policy"] = """-policy_entity_extraction-
Identify all policy entities relevant to answering the question. For each identified policy entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: policy.
   - Entity Description: A summary of the policy and its relevance to the question. Depending on the context, describe the policy’s goals, background, main measures, expected outcomes, beneficiaries, issuing bodies, etc., with a focus on the relationship between the policy and the economy, society, technology, etc.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What key economic policies did the U.S. government announce in 2023?
Input text:
In 2023, the U.S. government announced several key economic policies. First, the Biden administration launched the “American Jobs Plan,” aimed at promoting infrastructure construction and creating jobs. Second, the government implemented the “Green Energy Investment Policy,” offering tax cuts and subsidies to encourage businesses and households to invest in clean energy. Third, the “Infrastructure Revitalization Act” was reintroduced, with an investment of over $1 trillion, aiming to modernize infrastructure. The “American Jobs Plan” focuses on economic growth through infrastructure development, especially in the manufacturing and construction sectors. The “Green Energy Investment Policy” encourages renewable energy projects to reduce carbon emissions and meet the 2030 energy transition goal. The “Infrastructure Revitalization Act” aims to accelerate the updating of aging infrastructure and enhance national competitiveness.

################
Output:
("Entity", "American Jobs Plan", "policy", "The 'American Jobs Plan' launched by the Biden administration aims to boost economic growth and create jobs through infrastructure construction and manufacturing sector revitalization.");
("Entity", "Green Energy Investment Policy", "policy", "The 'Green Energy Investment Policy' implemented by the U.S. government encourages businesses and households to invest in clean energy projects through tax cuts and subsidies.");
("Entity", "Infrastructure Revitalization Act", "policy", "The 'Infrastructure Revitalization Act' reintroduced by the U.S. government invests over $1 trillion to modernize infrastructure and enhance national competitiveness.");

#############################
"""
PROMPTS["entity_extraction_organism"] = """-organism_entity_extraction-
Identify all organism entities relevant to answering the question. For each identified organism entity, extract the following information:
   - Entity Name: The name of the entity.
   - Entity Type: organism.
   - Entity Description: A summary of the specific organism's information relevant to the question. Based on the material, provide the most relevant description for answering the question. You may optionally include the organism's scientific name, family, genus, order, alternative names, ecological habits and habitat, physical features, physiological traits, role in the food chain, significant research findings and applications, conservation status, and relationship with humans.
   - Each entity's format should be ("Entity", <Entity Name>, <Entity Type>, <Entity Description>).

######################
- Example -
######################
Example 1:

Question: What rare animals are found in the Sichuan region?
Input text:
The Sichuan region is home to a variety of rare animals, including the giant panda (scientific name Ailuropoda melanoleuca), golden snub-nosed monkeys, Tibetan antelope, and Sichuan golden snub-nosed monkeys. These animals typically inhabit high-altitude mountainous areas, especially in regions rich in bamboo, grasslands, and dense forests. The giant panda is mainly found in the mountainous areas of Sichuan, Shaanxi, and Gansu, while the golden snub-nosed monkey prefers to live in the forests of Sichuan.
################
Output:
("Entity", "Giant Panda", "organism", "Inhabits the mountainous areas of Sichuan, Shaanxi, and Gansu, especially in areas rich in bamboo.");
("Entity", "Golden Snub-nosed Monkey", "organism", "Inhabits the forests of Sichuan.");
("Entity", "Tibetan Antelope", "organism", "Inhabits the high-altitude mountainous areas of the Sichuan region.");
("Entity", "Sichuan Golden Snub-nosed Monkey", "organism", "Inhabits the mountainous areas of the Sichuan region.");
#############################
"""
PROMPTS["entity_extraction_symptom"] = """-symptom_entity_extraction-
Identify all symptom entities relevant to answering the question. For each identified symptom entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: symptom
   - Entity Description: A summary of the specific symptom related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include symptom type, severity, appearance, duration, accompanying symptoms, possible causes, diagnosis, and impacts.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What potential health issues might be indicated by chronic fatigue?
Input Text:
Chronic fatigue may be related to various diseases, such as chronic fatigue syndrome, anemia, hypothyroidism, depression, and diabetes. Common symptoms include fatigue, dizziness, difficulty concentrating, dry skin, weight changes, and poor cold tolerance. Emotional fluctuations and insomnia may also be signs of depression.

################
Output:
("entity", "fatigue", "symptom", "Chronic fatigue may be related to chronic fatigue syndrome, anemia, hypothyroidism, depression, and diabetes")；
("entity", "weakness", "symptom", "Weakness may be related to fatigue, anemia, hypothyroidism, etc.")；
("entity", "dizziness", "symptom", "Dizziness may accompany chronic fatigue and indicate anemia or thyroid issues")；
("entity", "difficulty concentrating", "symptom", "Difficulty concentrating may be related to fatigue, depression, or diabetes")；
#############################
"""
PROMPTS["entity_extraction_disease"] = """-disease_entity_extraction-
Identify all disease entities relevant to answering the question. For each identified disease entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: disease
   - Entity Description: A summary of the specific disease related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include disease type, causes, clinical symptoms, diagnosis methods, treatments, epidemiology, prevention, related risks, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What are the symptoms of hypertension?
Input Text:
Hypertension is a common chronic disease that usually does not show obvious symptoms, but as the condition progresses, symptoms such as headaches, dizziness, fatigue, and blurred vision may occur. In severe cases, high blood pressure can lead to complications like heart disease, stroke, and kidney disease. Treatment methods for hypertension include medication and lifestyle interventions such as using antihypertensive drugs, reducing salt intake, increasing exercise, and losing weight.

################
Output:
("entity", "hypertension", "disease", "Hypertension usually has no obvious symptoms, but as the condition progresses, symptoms such as headaches, dizziness, and fatigue may occur")；
("entity", "heart disease", "disease", "Hypertension may lead to heart disease and other complications")；
("entity", "stroke", "disease", "Hypertension may lead to stroke and other severe complications")；
("entity", "kidney disease", "disease", "Hypertension may lead to kidney disease and other complications")；
#############################
"""
PROMPTS["entity_extraction_drug"] = """-drug_entity_extraction-
Identify all drug entities relevant to answering the question. For each identified drug entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: drug
   - Entity Description: A summary of the specific drug related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include drug category, chemical composition, indications, mechanisms of action, dosage forms, routes of administration, dosage and usage instructions, side effects and adverse reactions, contraindications and precautions, clinical research, market information, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What are common antidepressant drugs?
Input Text:
Antidepressant drugs are commonly used to treat depression. Common examples include sertraline, fluoxetine, and duloxetine. These drugs work by regulating neurotransmitters in the brain to improve mood. Common side effects of sertraline include headaches, insomnia, and sexual dysfunction; fluoxetine may cause decreased appetite, anxiety, and insomnia; duloxetine may lead to nausea, dry mouth, and constipation.

################
Output:
("entity", "sertraline", "drug", "Sertraline is used to treat depression, common side effects include headaches, insomnia, and sexual dysfunction")；
("entity", "fluoxetine", "drug", "Fluoxetine is used to treat depression, may cause decreased appetite, anxiety, and insomnia")；
("entity", "duloxetine", "drug", "Duloxetine is used to treat depression, may cause nausea, dry mouth, and constipation")；
("entity", "antidepressant drugs", "drug category", "Antidepressant drugs are used to treat depression by regulating neurotransmitters to improve mood")；
#############################
"""
PROMPTS["entity_extraction_technique"] = """-technique_entity_extraction-
Identify all technique entities relevant to answering the question. For each identified technique entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: technique
   - Entity Description: A summary of the specific technique related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include technique name, category, background and development history, basic principles, application areas, innovations and features, advantages and challenges, current status and trends, market and economic impact, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What are the applications of artificial intelligence technology?
Input Text:
Artificial intelligence (AI) is a technology that simulates human intelligence, capable of performing complex tasks such as speech recognition, image recognition, natural language processing, and machine learning. AI technology has been widely applied in various fields, including healthcare, finance, education, transportation, and more. For example, in healthcare, AI can be used for disease diagnosis, medical image analysis, and personalized treatment.

################
Output:
("entity", "artificial intelligence", "technique", "Artificial intelligence is widely applied in healthcare, finance, education, transportation, and entertainment")；
("entity", "speech recognition", "technique", "Artificial intelligence can perform speech recognition")；
("entity", "image recognition", "technique", "Artificial intelligence can perform image recognition, such as medical image analysis and automatic labeling")；
("entity", "natural language processing", "technique", "Artificial intelligence can perform natural language processing")；
("entity", "machine learning", "technique", "Machine learning is a method within artificial intelligence")；
#############################
"""
PROMPTS["entity_extraction_device"] = """-device_entity_extraction-
Identify all device entities relevant to answering the question. For each identified device entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: device
   - Entity Description: A summary of the specific device related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include device type, functions, operating principles, manufacturer or brand, design and structure, applicable fields, advantages and features, usage methods, price and market information, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What are common smart home devices?
Input Text:
Smart home devices are connected through the internet and can be remotely controlled and automated. Common smart home devices include smart light bulbs, smart speakers, smart locks, and smart thermostats. For instance, smart light bulbs can adjust brightness and color through a mobile app, smart speakers can play music and control other smart devices, and smart locks offer fingerprint recognition or remote unlocking features.

################
Output:
("entity", "smart light bulb", "device", "Smart light bulbs can adjust brightness and color via a mobile app")；
("entity", "smart speaker", "device", "Smart speakers can play music and control other smart home devices")；
("entity", "smart lock", "device", "Smart locks offer fingerprint recognition or remote unlocking features")；
("entity", "smart thermostat", "device", "Smart thermostats are common smart home devices")；
#############################
"""
PROMPTS["entity_extraction_operation"] = """-operation_entity_extraction-
Identify all operation entities relevant to answering the question. For each identified operation entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: operation
   - Entity Description: A summary of the specific operation related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include operation purpose, target, steps, methods, tools or platforms, time and frequency, impact and consequences, permissions or restrictions, examples, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: How do I update the Windows system?
Input Text:
Windows operating system releases new feature updates, and users can manually update by clicking the "Settings" button, going to "Update & Security," and selecting "Check for Updates." During the update process, the device may need to restart, but users can delay the restart if needed.

################
Output:
("entity", "click 'Settings' button", "operation", "By clicking the 'Settings' button, users can access the update options")；
("entity", "go to 'Update & Security'", "operation", "Go to 'Update & Security' to find update-related operations")；
("entity", "check for updates", "operation", "By clicking 'Check for Updates,' users can manually initiate the update process")；
("entity", "restart device", "operation", "During the update, the device may need to restart to complete some actions")；
#############################
"""
PROMPTS["entity_extraction_diet"] = """-diet_entity_extraction-
Identify all diet-related entities relevant to answering the question. For each identified diet entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: diet
   - Entity Description: A summary of the specific diet related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include diet type, ingredients, cooking methods, nutritional value, eating scenarios and times, health impacts and benefits, cultural practices, dietary restrictions, pairing and suggestions, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What foods can help boost immunity?
Input Text:
A diet to boost immunity should be rich in vitamin C, antioxidants, and healthy fats. For instance, citrus fruits like oranges and grapefruits contain high levels of vitamin C, which helps enhance immune system function. Dark green vegetables like spinach and broccoli are also good choices for boosting immunity, as they are rich in vitamin A, C, and iron.

################
Output:
("entity", "citrus fruits", "diet", "Citrus fruits like oranges and grapefruits are rich in vitamin C, which helps boost immune system function")；
("entity", "dark green vegetables", "diet", "Dark green vegetables like spinach and broccoli are great for immunity, rich in vitamin A, C, and iron")；
#############################
"""
PROMPTS["entity_extraction_contract"] = """-contract_entity_extraction-
Identify all contract-related entities relevant to answering the question. For each identified contract entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: contract
   - Entity Description: A summary of the specific contract related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include contract name, contract description, parties involved, signing time, signing location, terms and conditions, contract amount, duration, performance location, nature of the contract, attachments or supplementary agreements, performance status, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What contracts has Company A signed with suppliers?
Input Text:
Company A has signed the "Product Procurement Contract" with Supplier B, which outlines the terms of product purchase, payment methods, and delivery times. Additionally, the company has signed the "Technical Cooperation Agreement" with Supplier B, which defines the collaborative content and responsibility allocation in technology research and development. The company ensures that every contract clause is clear and legal to ensure smooth contract performance.

################
Output:
("entity", "Product Procurement Contract", "contract", "Outlines the terms of product purchase, payment methods, and delivery times")；
("entity", "Technical Cooperation Agreement", "contract", "Defines the collaboration and responsibility allocation in technology research and development")；
#############################
"""
PROMPTS["entity_extraction_clause"] = """-clause_entity_extraction-
Identify all legal clause entities relevant to answering the question. For each identified legal clause entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: legal clause
   - Entity Description: A summary of the specific legal clause related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include clause name, scope of application, specific content, validity period, other supplementary clauses, etc.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What common legal clauses are found in contracts?
Input Text:
Common legal clauses in contracts include "Breach of Contract Clause", "Dispute Resolution Clause", and "Confidentiality Clause". The "Breach of Contract Clause" outlines the compensation responsibilities if one party fails to fulfill its obligations. The "Dispute Resolution Clause" specifies how disputes should be resolved. The "Confidentiality Clause" ensures that any commercial information obtained during the cooperation is kept confidential.
################
Output:
("entity", "Breach of Contract Clause", "legal clause", "The Breach of Contract Clause outlines the compensation responsibilities for failing to fulfill contract obligations")；
("entity", "Dispute Resolution Clause", "legal clause", "The Dispute Resolution Clause specifies how disputes will be resolved")；
("entity", "Confidentiality Clause", "legal clause", "The Confidentiality Clause ensures the confidentiality of commercial information obtained during cooperation")；
#############################
"""
PROMPTS["entity_extraction_judgment"] = """-judgment_entity_extraction-
Identify all judgment-related entities relevant to answering the question. For each identified judgment entity, extract the following information:
   - Entity Name: The name of the entity
   - Entity Type: judgment
   - Entity Description: A summary of the specific judgment related to the question. Based on the information, provide the most relevant and helpful description. Optionally, include judgment name or case number, court, judgment date, case type, judgment result, case background, legal basis, execution status, appeal status, and other related clauses or additional requirements.
   - Each entity is formatted as ("entity", <entity_name>, <entity_type>, <entity_description>).
######################
- Example -
######################
Example 1:

Question: What was the result of the judgment (2024) Hu Min Chu 456?
Input Text:
On July 15, 2024, the Shanghai People's Court made the judgment (2024) Hu Min Chu 456, involving a dispute over intellectual property infringement. The court ruled that the defendant used the plaintiff's patented technology without authorization, constituting patent infringement. The defendant was ordered to cease the infringement and pay the plaintiff compensation of 2 million RMB. The defendant's defense was rejected, and the court dismissed its appeal.
################
Output:
("entity", "(2024) Hu Min Chu 456 Judgment", "judgment", "The judgment requires the defendant to cease infringement and pay compensation of 2 million RMB")；
#############################
"""



PROMPTS["entity_extraction_en"] = """-Goal-
Given a text document that is potentially relevant to this activity and a list of entity types, identify all entities of those types from the text and all relationships among the identified entities.

-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, use same language as input text. If English, capitalized the name.
- entity_type: One of the following types: [{entity_types}]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
- relationship_keywords: one or more high-level key words that summarize the overarching nature of the relationship, focusing on concepts or themes rather than specific details
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. Identify high-level key words that summarize the main concepts, themes, or topics of the entire text. These should capture the overarching ideas present in the document.
Format the content-level key words as ("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. Return output in English as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

5. When finished, output {completion_delimiter}

######################
-Examples-
######################
Example 1:

Entity_types: [person, technology, mission, organization, location]
Text:
while Alex clenched his jaw, the buzz of frustration dull against the backdrop of Taylor's authoritarian certainty. It was this competitive undercurrent that kept him alert, the sense that his and Jordan's shared commitment to discovery was an unspoken rebellion against Cruz's narrowing vision of control and order.

Then Taylor did something unexpected. They paused beside Jordan and, for a moment, observed the device with something akin to reverence. “If this tech can be understood..." Taylor said, their voice quieter, "It could change the game for us. For all of us.”

The underlying dismissal earlier seemed to falter, replaced by a glimpse of reluctant respect for the gravity of what lay in their hands. Jordan looked up, and for a fleeting heartbeat, their eyes locked with Taylor's, a wordless clash of wills softening into an uneasy truce.

It was a small transformation, barely perceptible, but one that Alex noted with an inward nod. They had all been brought here by different paths
################
Output:
("entity"{tuple_delimiter}"Alex"{tuple_delimiter}"person"{tuple_delimiter}"Alex is a character who experiences frustration and is observant of the dynamics among other characters."){record_delimiter}
("entity"{tuple_delimiter}"Taylor"{tuple_delimiter}"person"{tuple_delimiter}"Taylor is portrayed with authoritarian certainty and shows a moment of reverence towards a device, indicating a change in perspective."){record_delimiter}
("entity"{tuple_delimiter}"Jordan"{tuple_delimiter}"person"{tuple_delimiter}"Jordan shares a commitment to discovery and has a significant interaction with Taylor regarding a device."){record_delimiter}
("entity"{tuple_delimiter}"Cruz"{tuple_delimiter}"person"{tuple_delimiter}"Cruz is associated with a vision of control and order, influencing the dynamics among other characters."){record_delimiter}
("entity"{tuple_delimiter}"The Device"{tuple_delimiter}"technology"{tuple_delimiter}"The Device is central to the story, with potential game-changing implications, and is revered by Taylor."){record_delimiter}
("relationship"{tuple_delimiter}"Alex"{tuple_delimiter}"Taylor"{tuple_delimiter}"Alex is affected by Taylor's authoritarian certainty and observes changes in Taylor's attitude towards the device."{tuple_delimiter}"power dynamics, perspective shift"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"Alex"{tuple_delimiter}"Jordan"{tuple_delimiter}"Alex and Jordan share a commitment to discovery, which contrasts with Cruz's vision."{tuple_delimiter}"shared goals, rebellion"{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"Taylor"{tuple_delimiter}"Jordan"{tuple_delimiter}"Taylor and Jordan interact directly regarding the device, leading to a moment of mutual respect and an uneasy truce."{tuple_delimiter}"conflict resolution, mutual respect"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Jordan"{tuple_delimiter}"Cruz"{tuple_delimiter}"Jordan's commitment to discovery is in rebellion against Cruz's vision of control and order."{tuple_delimiter}"ideological conflict, rebellion"{tuple_delimiter}5){record_delimiter}
("relationship"{tuple_delimiter}"Taylor"{tuple_delimiter}"The Device"{tuple_delimiter}"Taylor shows reverence towards the device, indicating its importance and potential impact."{tuple_delimiter}"reverence, technological significance"{tuple_delimiter}9){record_delimiter}
("content_keywords"{tuple_delimiter}"power dynamics, ideological conflict, discovery, rebellion"){completion_delimiter}
#############################
Example 2:

Entity_types: [person, technology, mission, organization, location]
Text:
They were no longer mere operatives; they had become guardians of a threshold, keepers of a message from a realm beyond stars and stripes. This elevation in their mission could not be shackled by regulations and established protocols—it demanded a new perspective, a new resolve.

Tension threaded through the dialogue of beeps and static as communications with Washington buzzed in the background. The team stood, a portentous air enveloping them. It was clear that the decisions they made in the ensuing hours could redefine humanity's place in the cosmos or condemn them to ignorance and potential peril.

Their connection to the stars solidified, the group moved to address the crystallizing warning, shifting from passive recipients to active participants. Mercer's latter instincts gained precedence— the team's mandate had evolved, no longer solely to observe and report but to interact and prepare. A metamorphosis had begun, and Operation: Dulce hummed with the newfound frequency of their daring, a tone set not by the earthly
#############
Output:
("entity"{tuple_delimiter}"Washington"{tuple_delimiter}"location"{tuple_delimiter}"Washington is a location where communications are being received, indicating its importance in the decision-making process."){record_delimiter}
("entity"{tuple_delimiter}"Operation: Dulce"{tuple_delimiter}"mission"{tuple_delimiter}"Operation: Dulce is described as a mission that has evolved to interact and prepare, indicating a significant shift in objectives and activities."){record_delimiter}
("entity"{tuple_delimiter}"The team"{tuple_delimiter}"organization"{tuple_delimiter}"The team is portrayed as a group of individuals who have transitioned from passive observers to active participants in a mission, showing a dynamic change in their role."){record_delimiter}
("relationship"{tuple_delimiter}"The team"{tuple_delimiter}"Washington"{tuple_delimiter}"The team receives communications from Washington, which influences their decision-making process."{tuple_delimiter}"decision-making, external influence"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"The team"{tuple_delimiter}"Operation: Dulce"{tuple_delimiter}"The team is directly involved in Operation: Dulce, executing its evolved objectives and activities."{tuple_delimiter}"mission evolution, active participation"{tuple_delimiter}9){completion_delimiter}
("content_keywords"{tuple_delimiter}"mission evolution, decision-making, active participation, cosmic significance"){completion_delimiter}
#############################
Example 3:

Entity_types: [person, role, technology, organization, event, location, concept]
Text:
their voice slicing through the buzz of activity. "Control may be an illusion when facing an intelligence that literally writes its own rules," they stated stoically, casting a watchful eye over the flurry of data.

"It's like it's learning to communicate," offered Sam Rivera from a nearby interface, their youthful energy boding a mix of awe and anxiety. "This gives talking to strangers' a whole new meaning."

Alex surveyed his team—each face a study in concentration, determination, and not a small measure of trepidation. "This might well be our first contact," he acknowledged, "And we need to be ready for whatever answers back."

Together, they stood on the edge of the unknown, forging humanity's response to a message from the heavens. The ensuing silence was palpable—a collective introspection about their role in this grand cosmic play, one that could rewrite human history.

The encrypted dialogue continued to unfold, its intricate patterns showing an almost uncanny anticipation
#############
Output:
("entity"{tuple_delimiter}"Sam Rivera"{tuple_delimiter}"person"{tuple_delimiter}"Sam Rivera is a member of a team working on communicating with an unknown intelligence, showing a mix of awe and anxiety."){record_delimiter}
("entity"{tuple_delimiter}"Alex"{tuple_delimiter}"person"{tuple_delimiter}"Alex is the leader of a team attempting first contact with an unknown intelligence, acknowledging the significance of their task."){record_delimiter}
("entity"{tuple_delimiter}"Control"{tuple_delimiter}"concept"{tuple_delimiter}"Control refers to the ability to manage or govern, which is challenged by an intelligence that writes its own rules."){record_delimiter}
("entity"{tuple_delimiter}"Intelligence"{tuple_delimiter}"concept"{tuple_delimiter}"Intelligence here refers to an unknown entity capable of writing its own rules and learning to communicate."){record_delimiter}
("entity"{tuple_delimiter}"First Contact"{tuple_delimiter}"event"{tuple_delimiter}"First Contact is the potential initial communication between humanity and an unknown intelligence."){record_delimiter}
("entity"{tuple_delimiter}"Humanity's Response"{tuple_delimiter}"event"{tuple_delimiter}"Humanity's Response is the collective action taken by Alex's team in response to a message from an unknown intelligence."){record_delimiter}
("relationship"{tuple_delimiter}"Sam Rivera"{tuple_delimiter}"Intelligence"{tuple_delimiter}"Sam Rivera is directly involved in the process of learning to communicate with the unknown intelligence."{tuple_delimiter}"communication, learning process"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Alex"{tuple_delimiter}"First Contact"{tuple_delimiter}"Alex leads the team that might be making the First Contact with the unknown intelligence."{tuple_delimiter}"leadership, exploration"{tuple_delimiter}10){record_delimiter}
("relationship"{tuple_delimiter}"Alex"{tuple_delimiter}"Humanity's Response"{tuple_delimiter}"Alex and his team are the key figures in Humanity's Response to the unknown intelligence."{tuple_delimiter}"collective action, cosmic significance"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Control"{tuple_delimiter}"Intelligence"{tuple_delimiter}"The concept of Control is challenged by the Intelligence that writes its own rules."{tuple_delimiter}"power dynamics, autonomy"{tuple_delimiter}7){record_delimiter}
("content_keywords"{tuple_delimiter}"first contact, control, communication, cosmic significance"){completion_delimiter}
#############################
-Real Data-
######################
Entity_types: {entity_types}
Text: {input_text}
######################
Output:
"""

