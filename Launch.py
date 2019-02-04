# ===================================================================================== #
# author: Natalie Danezi <anatoli.danezi@surfsara.nl>   --  SURFsara                #
# helpdesk: Grid Services <grid.support@surfsara.nl>    --  SURFsara                #
#                                                                                   #
# usage: python pilot.py [picas_db_name] [picas_username] [picas_pwd]            #
# description:                                                                      #
#    Connect to PiCaS server with [picas_username] [picas_pwd]                   #
#    Get the next token in todo View                            #
#    Fetch the token parameters                             #
#    Run the main job (master_step23_v3.sh) with the proper input arguments        #
#    Get sterr and stdout in the output field of the token                #
# ===================================================================================== #

import sys
print("!!!!!!!!!!!!!!!!!!!!!")
print("!!!!!!!!!!!!!!!!!!!!!")
print("If you're seeing this, you're using the default GRID_PiCaS_Launcher branch")
print("This is no longer the master branch or the (working) version 0.1")
print("If anything fails or acts weird, then place this line in your launcher script")
print("\'git checkout v0.1 \'")
print("!!!!!!!!!!!!!!!!!!!!!!")
print("!!!!!!!!!!!!!!!!!!!!!!")
#python imports
import sys,os
import time
from GRID_PiCaS_Launcher import couchdb
from GRID_PiCaS_Launcher.get_picas_credentials import picas_cred
import subprocess
import shutil
import glob

#picas imports
from GRID_PiCaS_Launcher.picas.actors import RunActor
from GRID_PiCaS_Launcher.picas.clients import CouchClient
from GRID_PiCaS_Launcher.picas.iterators import BasicViewIterator
from GRID_PiCaS_Launcher.picas.modifiers import BasicTokenModifier
from GRID_PiCaS_Launcher.picas.executers import execute

#token imports
from GRID_PiCaS_Launcher.update_token_status import update_status
from GRID_PiCaS_Launcher.set_token_field import set_token_field
from GRID_PiCaS_Launcher.upload_attachment import upload_attachment
from GRID_PiCaS_Launcher.tok_to_bash import get_attachment


#from tok_to_bash import  export_tok_keys
from GRID_PiCaS_Launcher import sandbox
import pdb

class ExampleActor(RunActor):
    def __init__(self, iterator, modifier):
        self.iterator = iterator
        self.modifier = modifier
        self.client = iterator.client

    def create_sandbox(self, key='sandbox.json'):
        if key not in token['_attachments'].keys():
            print("WARNING: No sandbox configuration file")
            return
        cfg_file = token['_attachments'][key]
        sandbox = sandbox.Sandbox(config_file=cfg_file)
        sandbox.build_sandbox()

    def download_sandbox(self, token):
        downloader = None
        if 'SBXloc' in token.keys():
            location=token['SBXloc']
        else:
            return None
        if 'gsiftp' in location:
            downloader = sandbox.SandboxGSIDownloader(location)
        if 'https' in location or 'ftp' in location:
            downloader = sandbox.SandboxWgetDownloader(location)
        if downloader:
            downloader.download()
            downloader.check_download()
            downloader.extract_sandbox()
            downloader.remove_download_file()


    def process_token(self, key, token):
    # Print token information
        os.environ['TOKEN']=token['_id']
        from GRID_PiCaS_Launcher.tok_to_bash import  export_tok_keys

        self.token_name=token['_id'] 
        self.download_sandbox(token)
        subprocess.call(["chmod","a+x","master.sh"])
    
        print("Working on token: " + token['_id'])
#        export_tok_keys('tokvar.cfg',token)
    
        ## Read tokvar values from token and write to bash variables if not already exist! Save attachments and export abs filename to variable

        set_token_field(token['_id'],'status','launched',self.database,self.user,self.password)
        RUNDIR=os.getcwd() 

        #The launched script is simply master.sh with token and picas authen stored in env vars
        #master.sh takes the variables straight from the token. 
        command = "/usr/bin/time -v ./master.sh 2> logs_.err 1> logs_out"
        print("executing "+command)
        
        out = execute(command,shell=True)
        print('exit status is '+str(out))
        set_token_field(token['_id'],'output',out[0],self.database,self.user,self.password)
        if out[0]==0:
            set_token_field(token['_id'],'status','done',self.database,self.user,self.password)
        else:
            set_token_field(token['_id'],'status','error',self.database,self.user,self.password)
        
        os.chdir(RUNDIR)
        try:
           logsout = "logs_out"
           upload_attachment(token['_id'],logsout,self.database,self.user,self.password)
           logserr = "logs_.err"
           upload_attachment(token['_id'],logserr,self.database,self.user,self.password)
        except:
           pass

        #Just attaches all png files in the working directory to the token
        sols_search=subprocess.Popen(["find",".","-name","*.png","-o","-name","*.fits"],stdout=subprocess.PIPE)
        result=sols_search.communicate()[0]

        for png in result.split():
            upload_attachment(token['_id'],png,self.database,self.user,self.password,name=png)
            os.remove(png) 
        self.client.modify_token(self.modifier.close(self.client.db[self.token_name]))
        return

        

def main(url="https://picas-lofar.grid.surfsara.nl:6984", db=None, username=None, password=None):
    # setup connection to db
    db_name = sys.argv[1]
    client = CouchClient(url=url, db=db, username=username, password=password)
    # Create token modifier
    modifier = BasicTokenModifier()
    # Create iterator, point to the right todo view
    iterator = BasicViewIterator(client, sys.argv[4]+"/todo", modifier)
    # Create actor, takes one token from todo view
    actor = ExampleActor(iterator, modifier)
    actor.user = username
    actor.database = db
    actor.password = password
    # Start work!
    try:
        actor.run()
    except Exception as e:
        print("Exception occured")
        print(str(e.args))
#        set_token_field(actor.token_name,'status','error',actor.database,actor.p_usr,actor.password)
        set_token_field(actor.token_name,'launcher_status',str(e.args),actor.database,actor.user,actor.password)


if __name__ == '__main__':
    if len(sys.argv) == 5:
        db = str(sys.argv[1])
        username = str(sys.argv[2])
        password = str(sys.argv[3])
    else:
        pc = picas_cred()
        db = pc.database
        username = pc.user
        password = pc.password
    main(db=db, username=username, password=password)
