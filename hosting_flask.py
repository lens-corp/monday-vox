
from flask import Flask, request
from flask_ngrok import run_with_ngrok
from flask_cors import CORS
import numpy as np
from PIL import Image
app = Flask(__name__)
CORS(app)
run_with_ngrok(app)
import openai
import requests
import json
from monday import MondayClient
from datetime import date

class Monday_Voice_Class():
    def __init__(self):
        self.today = date.today()
        Monday_api_key = None #Your MONDAY KEY" 
        self.monday = MondayClient(Monday_api_key)
        self.Monday_base_url = 'https://api.monday.com/v2'
        openai.api_key = None # YOUR OPENAI KEY 
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': Monday_api_key
        }
        self.prompt = None
        self.ctr = 0
        self.board_id = None
        self.Action = -1        

    def get_boards(self):
        data = {
            'query': '{ boards { id, name } }'
        }
        response = requests.post("https://api.monday.com/v2", headers=self.headers, json=data)
        response_json = response.json()
        if 'errors' in response_json:
            error_message = response_json['errors'][0]['message']
            print(f"Error retrieving boards: {error_message}")
            return None

        boards = response_json['data']['boards']
        return boards

    def board_prompt(self, board_dict, prompt):    
        ops = "For the given prompt return a JSON output containing 2 keys." + """
        Prompt: """ + prompt + """ 
        Return the output in form of a JSON as shown below.

        Consider the following JSON Schema:
        {
        'Board_id': int,
        'Action': int,    
        }

        Board_id: Out of the following values present in the given dictionary. Give me the value of which key are we talking about in the given prompt.
        Action: For creating a new item the value of action is 0. for updating an existing item the value is 1. For deleting an item the value is 2.

        dictionary: """ + str(board_dict)  + """

        Make sure you only return the JSON having only 2 keys Board_id and Action. Nothing else.
        """
        return ops
    
    #############################################################################################################################

    def get_board_columns(self, board_id):
        data = {
            'query': 'query ($boardId: Int!) { boards (ids: [$boardId]) { columns { id, title, type } } }',
            'variables': {
                'boardId': board_id
            }
        }
        response = requests.post(self.Monday_base_url, headers=self.headers, json=data)
        response_json = response.json()

        if 'errors' in response_json:
            error_message = response_json['errors'][0]['message']
            print(f"Error retrieving board columns: {error_message}")
            return None
        columns = response_json['data']['boards'][0]['columns']
        return columns
    

    def create_final_addition_prompt(self,board_id, columns, prompt):
        txt_inp = """
        'myItemName': string,
        'columnVals':json.dumps({
        """
        for i in range(len(columns)):    
            id = columns[i]['id']
            key = ""
            types = ""
            if 'status' in id:
                key = "label"
                types = "string"
                meaning = columns[i]['title']
                txt_inp += str(id) + ": {"+ key + ":" + types + "}, # This means " + meaning + " \n"
            elif 'date' in id:
                key ='date'
                types = "date"
                meaning = columns[i]['title']
                txt_inp += str(id) + ": {"+ key + ":" + types + "}, # This means " + meaning + " \n"
            elif 'priority' in id:
                key = "label"
                types = "string"
                meaning = columns[i]['title']
                txt_inp += str(id) + ": {"+ key + ":" + types + "}, # This means " + meaning + " \n"
            elif  "text" in id:
                key = "text"
                types = "string"
                meaning = columns[i]['title']
                txt_inp += str(id) + ": " + types + ", # This means " + meaning + " \n"
            else:
                continue            

        txt_inp += "})"        
        pmt = """You are going to write a JSON content for the given prompt. Todays date is """ + str(self.today) + """.

        Prompt: """ + prompt + " \n" + txt_inp + """

        myItemName should contain only the name of the task.
        Any key starting with status can take one of the 3 values only: "Working on it", "Done", "Stuck".
        Any key starting with date can take the date in yyyy-mm-dd format. 
        Any key starting with priority can take one of the 4 values only: "Critical ⚠️️", "High", "Medium", "Low".

        If Any of them is not present then write ''.
                    
        In the response, include only the JSON. Do not miss any comma. 
        The output should be JSON Only. """

        return pmt

    #################################################ADD ITEM ON MONDAY.COM######################################################
    def Add_Item_Monday(self):
        columns = self.get_board_columns(self.board_id)
        pmt = self.create_final_addition_prompt(self.board_id, columns, self.prompt)
        ctr = 3
        while(True):
            ctr += 1
            if ctr == 10:
                # Response1 = "Sorry! Can't Complete your request."
                # tts = gTTS(Response1, lang="en")
                # output_audio_file = "output.mp3"
                # tts.save(output_audio_file)
                return 0
            try:
                prompt_response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role":"user", "content": pmt}], 
                        max_tokens = 500
                    )
                res = json.loads(prompt_response.choices[0].message.content)                
                break
            except:
                continue

        query5 = 'mutation ($myItemName: String!, $columnVals: JSON!) { create_item (board_id:' + str(self.board_id) + ', item_name:$myItemName, column_values:$columnVals) { id } }'

        vars = {
            'myItemName': res['myItemName'],    
            'columnVals': json.dumps(res['columnVals'])
        }
        data = {'query': query5, 'variables': json.dumps(vars)}
        r = requests.post(url=self.Monday_base_url, json=data, headers=self.headers)
        return 1
        # print(r.json())
        
    ################################################## Create UPDATE Response for Monday.com #############################################

    def create_final_updation_prompt(self, titles, change_prompt):        
        ops = "Given the columns of table: """ + str(titles)+""" Please provide the names of the columns that should be used for filtering and the names of the columns that need to be changed based on the given prompt.\nColumns for filtering:\nValues for filtering:\nColumns for changes:\nValue for update: "
        Prompt: """ + change_prompt + """ 
        Return the output in form of a JSON as shown below.

        Consider the following JSON Schema:

        'Columns_for_filtering': list,
        'Values_for_filtering': list,
        'Columns_for_change': list,
        'Values_for_update': list 

        If any of the value is a date. Then write it in this form yyyyy-mm-dd.
        Status can take one of the 3 values only: "Working on it", "Done", "Stuck".
        Priority can take one of the 4 values only: "Critical ⚠️️", "High", "Medium", "Low".        
        for the given columns, column named 'Name' represents the name of that item or task.
        
        Remember Columns_for_filtering should contain only the names from given columns that are really necessary for filtering. Do not assume anything. Give output based on given information only.
        Remember that Values_for_filtering should only contain the values correponding to Columns_for_filtering.

        check it once, whether the Columns_for_filtering is containing only the relevant information or not.
        
        Make sure you only return the JSON. Nothing else.
        """
        return ops

    def update_items_based_on_res(self, column_dict, ops):    
        outs = []
        for i in range(len(ops['Columns_for_filtering'])):    
            outs.append([self.monday.items.fetch_items_by_column_value(self.board_id, column_dict[ops['Columns_for_filtering'][i]], ops['Values_for_filtering'][i])])

        all_items = []
        for i in range(len(outs)):
            list1 = []
            for j in range(len(outs[i])):
                items = outs[i][j]['data']['items_by_column_values']        
                for k in range(len(items)):
                    list1.append(items[k]['id'])
            all_items.append(list1)
        
        print("All ITEMS: " ,all_items)
        common_elements = set(all_items[0])
        for lst in all_items[1:]:
            common_elements.intersection_update(lst)
        print("Common ITEMS: ", common_elements)        
        for elems in common_elements:
            for i in range(len(ops['Columns_for_change'])):
                if 'status' in column_dict[ops['Columns_for_change'][i]]:
                    res = self.monday.items.change_item_value(self.board_id, elems, column_dict[ops['Columns_for_change'][i]], {"label" : ops["Values_for_update"][i]})
                
                elif 'priority' in column_dict[ops['Columns_for_change'][i]]:
                    res = self.monday.items.change_item_value(self.board_id, elems, column_dict[ops['Columns_for_change'][i]], {"label" : ops["Values_for_update"][i]})

                elif 'date' in column_dict[ops['Columns_for_change'][i]]:
                    res = self.monday.items.change_item_value(self.board_id, elems, column_dict[ops['Columns_for_change'][i]], {"date" : ops["Values_for_update"][i]})
                
                elif 'text' in column_dict[ops['Columns_for_change'][i]]:
                    res = self.monday.items.change_item_value(self.board_id, elems, column_dict[ops['Columns_for_change'][i]], ops["Values_for_update"][i])
                
                elif 'name' in column_dict[ops['Columns_for_change'][i]]:
                    res = self.monday.items.change_item_value(self.board_id, elems, column_dict[ops['Columns_for_change'][i]], ops["Values_for_update"][i])
                else:
                    res = column_dict[ops['Columns_for_change'][i]] + " NOT SUPPORTED"
                print(res)

    def Change_Item_Monday(self):
        columns = self.get_board_columns(self.board_id)
        column_dict = {}
        titles = []
        for i in range(len(columns)):
            column_dict[columns[i]['title']] = columns[i]['id']
            titles.append(columns[i]['title'])

        pmt = self.create_final_updation_prompt(titles, self.prompt)    
        ctr = 3
        while(True):
            ctr += 1
            if ctr == 10:
                # Response1 = "Sorry! Can't Complete your request."
                # tts = gTTS(Response1, lang="en")
                # output_audio_file = "output.mp3"
                # tts.save(output_audio_file)
                return 0
                        
            prompt_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role":"user", "content": pmt}], 
                    max_tokens = 500
                )    
            res = prompt_response.choices[0].message.content
            try:
                ops = json.loads(res)
                break
            except:            
                try:
                    ops = json.loads("{" + res.split("{")[-1])
                    break
                except:
                    continue
        print(ops)
        self.update_items_based_on_res(column_dict, ops)
        return 1
        
    def create_final_deletion_prompt(self,titles, change_prompt):
        ops = "Given the columns of table: """ + str(titles)+""" Provide me a list of names of columns that has to be deleted along with value based on which we have to delete."
        Prompt: """ + change_prompt + """ 
        Return the output in form of a JSON as shown below.

        Consider the following JSON Schema:

        'Columns_for_deletion': list,
        'Values_for_deletion': list,    

        If any of the value is a date. Then write it in this form yyyyy-mm-dd.
        Status can take one of the 3 values only: "Working on it", "Done", "Stuck".
        Priority can take one of the 4 values only: "Critical ⚠️️", "High", "Medium", "Low".        
        for the given columns, column named 'Name' represents the name of that item or task.

        If the data is not sufficient to assign a value for a given column, do not add that column in the list.        

        Make sure you only return the JSON. Nothing else.
        """
        return ops

    def delete_items_based_on_res(self, column_dict, ops):
        outs = []
        for i in range(len(ops['Columns_for_deletion'])):    
            outs.append([self.monday.items.fetch_items_by_column_value(self.board_id, column_dict[ops['Columns_for_deletion'][i]], ops['Values_for_deletion'][i])])

        all_items = []
        for i in range(len(outs)):
            list1 = []
            for j in range(len(outs[i])):
                items = outs[i][j]['data']['items_by_column_values']        
                for k in range(len(items)):
                    list1.append(items[k]['id'])
            all_items.append(list1)
        
        common_elements = set(all_items[0])
        for lst in all_items[1:]:
            common_elements.intersection_update(lst)
        
        for elems in common_elements:        
            res = self.monday.items.delete_item_by_id(elems)
            print(res)

    def Delete_Item_Monday(self):
        columns = self.get_board_columns(self.board_id)
        column_dict = {}
        titles = []
        for i in range(len(columns)):
            column_dict[columns[i]['title']] = columns[i]['id']
            titles.append(columns[i]['title'])

        pmt = self.create_final_deletion_prompt(titles, self.prompt)    
        ctr = 3
        while(True):
            ctr += 1
            if ctr == 10:                              
                return 0
                        
            prompt_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role":"user", "content": pmt}], 
                    max_tokens = 500
                )    
            res = prompt_response.choices[0].message.content
            print(res)
            try:
                ops = json.loads(res)
                if len(ops['Columns_for_deletion']) == len(ops['Values_for_deletion']):
                    break
            except:            
                try:
                    ops = json.loads("{" + res.split("{")[-1])
                    if len(ops['Columns_for_deletion']) == len(ops['Values_for_deletion']):
                        break                    
                except:
                    continue
        
        print(ops)
        self.delete_items_based_on_res(column_dict, ops)
        return 1


    def main_runs(self, prompt):
        ############################################### GET BOARDS and CONVERT TO DICT ###############################################
        self.prompt = prompt
        boards = self.get_boards()
        boards_dict = {}
        for i in range(len(boards)):
            boards_dict[boards[i]['name']] = boards[i]['id']

        print(boards_dict)
        self.ctr = 0
        ############################################### ASK GPT WHICH BOARD ARE WE TALKING ABOUT #####################################
        Action = -1
        while (True):
            self.ctr += 1
            if self.ctr == 4:
                print("BAD QUERY")
                break
            try:
                response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role":"user", "content": self.board_prompt(boards_dict, prompt)}],
                        max_tokens = 50
                    )
                op1 = json.loads(response.choices[0].message.content)
                self.board_id = int(op1['Board_id'])
                self.Action = int(op1['Action'])
                break
            except:
                print(response.choices[0].message.content)
                continue    
                
        print("BOARD ID: ", self.board_id)
        print("Action: ", self.Action)
        
        Response1 = "Sorry! Cannot complete your request. Try Again."
        if self.Action == 0:
            if self.Add_Item_Monday():
                Response1 = "Your request is completed. Item Successfully Added."                

        elif self.Action == 1:
            if self.Change_Item_Monday():
                Response1 = "Your request is completed. Board Successfully Modified."                

        elif self.Action == 2:
            if self.Delete_Item_Monday():
                Response1 = "Your request is completed. Item successfully Deleted."                
        else:    
            Response1 = "Sorry! Can't understand what you want me to do."            
        return Response1
        

obj = Monday_Voice_Class()

@app.route('/getText', methods=['GET'])
def getting_input():
    val = request.get_json()['query']    
    text_output = obj.main_runs(val)
    return {
        'Result': text_output
    }

if __name__ == "__main__":
    app.run()
