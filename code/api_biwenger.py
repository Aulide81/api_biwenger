
import requests
import pickle
import json
import pandas as pd
from pprint import pprint


class biwenger:
  
  """
  Clase que permite obtener informacion de una sesion
  en la web/app de As Biwenger
  
  Para inicializar una instancia precisa:
    - mail
    - password
    
  Argumentos opcionales:
    - id_league: el id de la liga a la que queremos acceder
    - id_user: el id del usuario de la liga que queremos acceder
    
  Si desconocemos las ligas que disponemos, será necesario listar
  las ligas disponibles .leagues() y configurar liga mediante .set_league()
    
  """
  
  def __init__(self, mail, password, id_league=None, id_user=None):
    
    self.mail=mail
    self.password=password
    self.token=self.__get_token__(mail,password)
    self.leagues=self.__get_leagues__()
    
    #funcion que valide liga y usuario con la informacion en self.leagues
    
    self.id_league = str(id_league)
    self.id_user = str(id_user)
    
    if ((id_league is None) | (id_user is None)):
      self.users = None
    else:
      self.users = self.__get_users__()
      
    self.balance = None
    
    
    
  def __str__(self):
    if not self.token is None:
      return("Sesion iniciada correctamente con {mail}".format(mail=self.mail))
    else:
      return("No se ha iniciado sesion")

  def __get_token__(self, mail, password):
    url = "https://biwenger.as.com/api/v2/auth/login"
    login_data = dict(email = mail, password = password)
    response = requests.session().post(url, data = login_data)
    token = response.json()['token']
    return(token)
  
  def __get_leagues__(self):
    url="https://biwenger.as.com/api/v2/account"
    leagues = requests.get(url, headers={'authorization':'Bearer '+ self.token})
    leagues=leagues.json()['data']['leagues']
    leagues={ l["name"]:{'id_league':l['id'], 'id_user':l['user']['id'], 'name':l['user']['name']} for l in leagues}
    return(leagues)
    
  def __get_users__(self):
    url="https://biwenger.as.com/api/v2/league?include=all,-lastAccess&fields=*,standings,tournaments,group,settings(description)"
    liga = requests.get(url, headers={'authorization':'Bearer '+ self.token, 'x-league': self.id_league, 'x-user': self.id_user})
    diccionario=liga.json()
    participantes = diccionario['data']['standings']
    participantes={j['name']:j['id'] for j in participantes}
    return(participantes)
  
  def set_league(self, id_league, id_user):
    
    #funcion que valide liga y usuario con la informacion en self.leagues
    
    self.id_league=str(id_league)
    self.id_user=str(id_user)
    self.users = self.__get_users__()

  def restart_balance(self):
    participantes=self.users
    balance={j:{0:50000000} for j in participantes.keys()}
    balance['__ult.act']=0
    self.balance=balance
      
  def load_balance(self, path):
    with open(path, "rb") as file:
      balance=pickle.load(file)
      self.balance=balance
      
  def save_balance(self, path):
    with open(path, "wb") as file:
      pickle.dump(self.balance,file)
      
  def update_balance(self, limit=500):
    
    if self.balance is None:
      
      print("No se ha inicializado/cargado el balance")
      return(None)
    
    else:
      
      url="https://biwenger.as.com/api/v2/league/1648876/board?offset=0&limit={limit}".format(limit=limit)
      home = requests.get(url, headers={'authorization':'Bearer '+ self.token, 'x-league': self.id_league, 'x-user': self.id_user})
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
                  self.balance[comprador][date+pos+1]=-amount
                else:
                  self.balance[comprador][date]=-amount

              
              # Hay "vendedor"?
              
              if 'from' in mov.keys():
                vendedor=mov['from']['name']
                
                if  date in self.balance[vendedor].keys():
                  self.balance[vendedor][date+pos+1]=amount
                else:
                  self.balance[vendedor][date]=amount
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
    players = requests.get(url)
    players = json.loads(players.text[17:-1])['data']['players']
    df_players = pd.DataFrame(players)
    df_players = df_players.transpose()
    df_players.index = df_players.index.astype(int)
    return(df_players)
  
  def team(self, user = None):
    if user is None:
      user=self.id_user
    url="https://biwenger.as.com/api/v2/user/{user}?fields=*,account(id),players(id,owner),lineups(round,points,count,position),league(id,name,competition,type,mode,marketMode,scoreID),market,seasons,offers,lastPositions".format(user=user)
    team = requests.get(url, headers={'authorization':'Bearer '+ self.token, 'x-league': self.id_league, 'x-user': self.id_user})
    team = team.json()['data']['players']
    team = pd.Series({player['id']:player['owner']['price'] for player in team})
    team = pd.DataFrame(team,columns=["Pvp"])
    players = self.get_players()
    team = team.join(players)
    
    team['Beneficio'] = team.price - team.Pvp
    
    columnas=['id', 'name','price','Pvp','Beneficio','priceIncrement',
    'points','position', 'status', 'playedHome', 'playedAway',
    'fitness', 'pointsHome', 'pointsAway', 'pointsLastSeason',
    'statusInfo','slug','teamID','fantasyPrice']
    
    return(team[columnas])
