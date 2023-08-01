
import requests
import pickle
import json
import pandas as pd
from pprint import pprint


class biwenger:
  
  def __init__(self, mail, password):
    self.mail=mail
    self.password=password
    self.token=self.__get_token__(mail,password)
    self.balance=None
    
  def __get_token__(self, mail, password):
    url = "https://biwenger.as.com/api/v2/auth/login"
    login_data = dict(email = mail, password = password)
    response = requests.session().post(url, data = login_data)
    token = response.json()['token']
    return(token)
  
  def __str__(self):
    if not self.token is None:
      return("Sesion iniciada correctamente con {mail}".format(mail=self.mail))
    else:
      return("No se ha iniciado sesion")

  def create_balance(self, league=1648876, usuario=9997844):
    
    if self.balance is None:
      url="https://biwenger.as.com/api/v2/league?include=all,-lastAccess&fields=*,standings,tournaments,group,settings(description)"
      liga = requests.get(url, headers={'authorization':'Bearer '+ self.token, 'x-league': str(league), 'x-user': str(usuario)})
      diccionario=liga.json()
      balance = diccionario['data']['standings']
      balance={j['name']:{0:50000000} for j in balance}
      balance['__ult.act']=0
      self.balance=balance
      
  def load_balance(self, path):
    with open(path, "rb") as file:
      balance=pickle.load(file)
      self.balance=balance
      
  def save_balance(self, path):
    with open(path, "wb") as file:
      pickle.dump(self.balance,file)
      
  def update_balance(self,league=1648876, usuario=9997844, limit=500):
    
    if self.balance is None:
      
      print("No se ha inicializado/cargado el balance")
      return(None)
    
    else:
      
      url="https://biwenger.as.com/api/v2/league/1648876/board?offset=0&limit={limit}".format(limit=limit)
      home = requests.get(url, headers={'authorization':'Bearer '+ self.token, 'x-league': str(league), 'x-user': str(usuario)})
      diccionario=home.json()
      muro=diccionario['data']
      ult_act=self.balance['__ult.act']
      date0=0
      
      # Actualizamos
      
      for div in muro:
        
        if ( div['type'] in ["transfer","market"] ):
          
          date=div['date']
          
          if date0<date:
            
            date0=date
            
          if (date > ult_act):
            
            movs=div['content']
            
            for pos,mov in enumerate(movs):
              
              amount=mov['amount']
              
              # Hay comprador?
              
              if 'to' in mov.keys():
                comprador=mov['to']['name']
                
                if  date in self.balance[comprador].keys():
                  self.balance[comprador][date]=-amount
                else:
                  self.balance[comprador][date+pos+1]=-amount

              
              # Hay "vendedor"?
              if 'from' in mov.keys():
                vendedor=mov['from']['name']
                
                if  date in self.balance[vendedor].keys():
                  self.balance[vendedor][date]=amount
                else:
                  self.balance[vendedor][date+pos+1]=amount
          else:
            
            break
            
      self.balance['__ult.act']=date0
    
  def summary(self):
    
    for player in self.balance.keys():
      try:
        amount=sum([v for v in self.balance[player].values()])
        print(player,f"{amount:,}"," euros")
      except:
        pass
  
  def get_players(self):
    url="https://cf.biwenger.com/api/v2/competitions/la-liga/data?lang=es&score=3&callback=jsonp_1465365484"
    lista_jugadores = requests.get(url)
    lista_jugadores=json.loads(lista_jugadores.text[17:-1])['data']['players']
    
    df=pd.DataFrame(lista_jugadores)
    df=df.transpose()
    return(df)
