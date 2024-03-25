from dataclasses import dataclass
from typing import Union
from support_bot.storage import Storage

@dataclass
class TicketLabelData():
    label_id: int
    name: str
    description:str
    hex_color:str
    
    def __init__(self, label_id:int, name:str, description:str, hex_color:str):
        self.label_id = label_id
        self.name = name
        self.description = description
        self.hex_color = hex_color

class TicketLabelsRepository(object):
    def __init__(self, storage:Storage) -> None:
        self.storage = storage
        
    def create_label(self, name:str, description:str, hex_color:str) -> Union[int, None]:
        self.storage._execute("""
            insert into TicketLabels (name, description, hex_color) values (?,?,?) RETURNING id;
        """, (name, description, hex_color,))
        inserted_id = self.storage.cursor.fetchone()
        if inserted_id:
            return inserted_id[0]
        return inserted_id
        
    def get_label(self, label_id:int) -> Union[int, None]:
        self.storage._execute("SELECT id FROM TicketLabels WHERE id= ?;", (label_id,))
        id = self.storage.cursor.fetchone()
        if id:
            return id[0]
        return id
    
    def delete_label(self, label_id:int):
        self.storage._execute("""
            DELETE FROM TicketLabels WHERE id= ?;
        """, (label_id,))
        
    def get_all_fields(self, label_id:int) -> TicketLabelData:
        self.storage._execute("""
            select id, name, description, hex_color from TicketLabels where id = ?;
        """, (label_id,))
        row = self.storage.cursor.fetchone()
        return TicketLabelData(*row)
    
    def set_label_name(self, label_id:int, name:str):
        self.storage._execute("""
            UPDATE TicketLabels SET name= ? WHERE id=?
        """, (name, label_id))
            
    def set_label_description(self, label_id:int, description:str):
        self.storage._execute("""
            UPDATE TicketLabels SET description= ? WHERE id=?
        """, (description, label_id))
            
    def set_label_color(self, label_id:int, color:str):
        self.storage._execute("""
            UPDATE TicketLabels SET color= ? WHERE id=?
        """, (color, label_id))
    
    def assign_label_to_ticket(self, label_id:int, ticket_id: int):
        self.storage._execute("""
            insert into TicketsTicketLabelsRelation (ticket_label_id, ticket_id) values (?, ?);
        """, (label_id, ticket_id,))
        
    def remove_label_from_ticket(self, label_id:int, ticket_id: int):
        self.storage._execute("""
            DELETE FROM TicketsTicketLabelsRelation WHERE ticket_label_id= ? AND ticket_id= ?
        """, (label_id, ticket_id))
        
    def get_all_labels(self) -> [TicketLabelData]:
        self.storage._execute("""
            SELECT id, name, description, hex_color from TicketLabels
        """, ())

        labels = self.storage.cursor.fetchall()
        return [TicketLabelData(*label) for label in labels]

    def get_ticket_label_ids(self, ticket_id:int) -> [int]:
        self.storage._execute("""
            SELECT ticket_label_id FROM TicketsTicketLabelsRelation WHERE ticket_id = ?;
        """, (ticket_id,))

        label_ids = self.storage.cursor.fetchall()
        return [label_id[0] for label_id in label_ids]