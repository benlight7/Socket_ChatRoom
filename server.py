import socket
import threading #multithreading
import json #JSON FORMAT
import sqlite3 #DB
import string #generate token
import random
import sys #argv[1], argv[2]
import stomp

# 目前是GROUP資料表採取:「每一筆資料 |token|group_name|紀錄」 eg. Group_A 有aa,bb,cc三個成員，會有三筆資料 |aa|Group_A|,|bb|Group_A|,|cc|Group_A|
class Response():
    # JSON message dictionary
    #------------------------------------------------#
    ## 1.register
    success = { 'status': 0, 'message': 'Success!' }
    existuser = { 'status': 1, 'message': '' } #need <id>

    ## 2.login
    gettoken = { 'status': 0, 'token': '', 'message': 'Success!' , 'usergroup': []} #need <token>
    nouser = { 'status': 1, 'message': 'No such user or password error'}

    ## 3.delete
    '''success'''
    notlogin = { 'status': 1, 'message': 'Not login yet'}

    ## 4.logout
    bye = { 'status': 0, 'message': 'Bye!'}
    '''notlogin'''

    ## 5.invite
    '''success'''
    isfriend = { 'status': 1, 'message': ''} #need <id>
    notexist = { 'status': 1, 'message': ''} #need <id>
    '''notlogin'''
    yourself = { 'status': 1, 'message': 'You cannot invite yourself'}
    haveinvite = { 'status': 1, 'message': 'Already invited'}
    otherinviteyou = { 'status': 1, 'message': ''} #need <id>

    ## 6.list-invite
    listinvite = { 'status': 0, 'invite': []} #need [userA, userB]
    '''notlogin'''

    ## 7.accept-invite
    '''success'''
    notinviteyou = { 'status': 1, 'message': ''} #need <id>
    '''notlogin'''

    ## 8.list-friend
    listfriend = { 'status': 0, 'friend': []} #need [userA, userB]
    '''notlogin'''

    ## 9.post
    '''success'''
    '''notlogin'''

    ## 10.receive-post
    recvpost = { 'status': 0, 'post': []} #need [{“id”: user_A, “message”: “I have no friends”}, {“id”: user_B,“message”: “I have no friends too” }]
    '''notlogin'''

    # STOMP
    ## 1.send
    '''success'''
    '''Fail-A:notlogin'''
    '''Fail-B:Usage'''
    '''Fail-C:notexist'''
    notyourfriend = { 'status': 1, 'message': ''}
    notonline = { 'status': 1, 'message': ''}

    ## 2.create-group
    existgroup = { 'status': 1, 'message': ''}

    ## 3.list-group
    listallgroup = { 'status': 0, 'allgroup': []}

    ## 4.list-joined
    listjoinedgroup = { 'status': 0, 'joinedgroup': []}

    ## 5.join-group
    ismember = { 'status': 1, 'message': ''}

    ## 6.send-group
    notmember = { 'status': 1, 'message': ''}


'''---USER, SOCIAL, GROUP---'''
def USERid_exist(cursor, id):
    cursor.execute('SELECT EXISTS (SELECT * FROM "USER" WHERE id = ?)', (id, ) )
    exist = cursor.fetchone()
    return exist[0]

def USERtoken_exist(cursor, token):
    cursor.execute('SELECT EXISTS (SELECT * FROM "USER" WHERE token = ?)', (token, ) )
    exist = cursor.fetchone()
    return exist[0]

def Social_exist(cursor, token):
    cursor.execute('SELECT EXISTS (SELECT * FROM "SOCIAL" WHERE token = ?)', (token, ) )
    exist = cursor.fetchone()
    return exist[0]

def GetSocial(cursor, token):
    cursor.execute('SELECT * FROM "SOCIAL" WHERE token = ?', (token, ) )
    return cursor
    #0:token / 1:who_invite_you / 2:friend / 3:receive-post

def GROUP_token_exist(cursor, token):
    cursor.execute('SELECT EXISTS (SELECT * FROM "GROUP" WHERE token = ?)', (token, ) )
    exist = cursor.fetchone()
    return exist[0]

def GetJoinedGroup(cursor, token): # for 'list-joined'
    cursor.execute('SELECT * FROM "GROUP" WHERE token = ?', (token, ) )
    return cursor
    #0:token / 1:group

def GetAllGroup(cursor): # for 'list-group'
    cursor.execute('SELECT * FROM "GROUP"')
    return cursor
    #0:token / 1:group

'''---Get Info---'''
def GetToken(cursor, id):
    cursor.execute('SELECT "token" FROM "USER" WHERE id = ?', (id, ) )
    token = cursor.fetchone()
    return token[0]

def GetId(cursor, token):
    cursor.execute('SELECT "id" FROM "USER" WHERE token = ?', (token, ) )
    id = cursor.fetchone()
    return id[0]

def LoginStatus(cursor, token):
    cursor.execute('SELECT logined FROM "USER" WHERE token = ?', (token, ) )
    status = cursor.fetchone()
    return status[0]

'''---Random String---'''
def random_string(size=15, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def TCP(sock, addr):
    # Receive connection from client side
    print('accept new connection from %s:%s...' %addr)
    
    # open database
    db = sqlite3.connect('userinfo.db')
    cursor = db.cursor()

    # receive command from client.py
    data = sock.recv(1024).decode()
    cmd    = data.split(' ', 2)[0] if len( data.split(' ', 2) ) >= 1 else ''
    second = data.split(' ', 2)[1] if len( data.split(' ', 2) ) >= 2 else ''
    third  = data.split(' ', 2)[2] if len( data.split(' ', 2) ) == 3 else ''

    if cmd == 'post' and len( data.split(' ') ) > 3:
        third  = data.split(' ')[2:] 
    if (cmd == 'send' or cmd == 'send-group') and len( data.split(' ') ) >= 4:
        third = data.split(' ')[2]
        fourth  = data.split(' ')[3:]

    if cmd == 'register':
        #USAGE_error
        if len( data.split(' ') ) != 3:
            resp = { 'status': 1, 'message': 'Usage: register ​<id>​ ​<password>' }
        else:
            #check whether USER.id already exists 
            cursor.execute('SELECT EXISTS (SELECT * FROM "USER" WHERE id = ?)', (second,) )
            exist = cursor.fetchone()
            #INSERT (id, pw, token)
            if exist[0] == 0:
                cursor.execute('INSERT INTO "USER" (id, pw, token, logined) \
                                VALUES (?, ?, ?, 0)', (second, third, random_string()+second) )
                resp = Response().success
            #USER.id already exists
            else:
                resp = Response().existuser
                resp['message'] = ('%s is already used' %second) 

    elif cmd == 'login':
        #USAGE_error
        if len( data.split(' ') ) != 3:
            resp = { 'status': 1, 'message': 'Usage: login ​<id>​ ​<password>' }
        else:
            cursor.execute('SELECT EXISTS (SELECT * FROM "USER" WHERE id = ? AND pw = ?)', (second, third) )
            exist = cursor.fetchone()
            if exist[0] == 0:
                resp = Response().nouser
            else:
                #USER.logined = 1
                cursor.execute('UPDATE "USER" SET logined = 1 WHERE id = ?', (second, ) )
                #Get token
                resp = Response().gettoken
                resp['token'] = GetToken(cursor, second)
                #Get usergroup
                group_array = []
                if GROUP_token_exist(cursor, GetToken(cursor, second)) == 1:  
                    for row in GetJoinedGroup(cursor, GetToken(cursor, second)):
                        if row[1] != None:
                            group_array.append(row[1])
                resp['usergroup'] = group_array   


    elif cmd == 'delete':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 2:
                resp = { 'status': 1, 'message': 'Usage: delete ​<user>​' }
            else:
                #check whether USER.logined = 0
                if LoginStatus(cursor, second) == 0:
                    resp = Response().notlogin
                else:
                    #delete GROUP
                    if GROUP_token_exist(cursor, second) == 1:
                        cursor.execute('DELETE FROM "GROUP" WHERE token = ?', (second, ) )
                    #delete SOCIAL
                    if Social_exist(cursor, second) == 1:
                        cursor.execute('DELETE FROM "SOCIAL" WHERE who_invite_you = ?', (GetId(cursor, second), ) )
                        cursor.execute('DELETE FROM "SOCIAL" WHERE friend = ?', (GetId(cursor, second), ) )
                        cursor.execute('DELETE FROM "SOCIAL" WHERE whopost = ?', (GetId(cursor, second), ) )
                        cursor.execute('DELETE FROM "SOCIAL" WHERE token = ?', (second, ) )
                    #delete USER
                    cursor.execute('DELETE FROM "USER" WHERE token = ?', (second, ) )
                    resp = Response().success

    elif cmd == 'logout':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 2:
                resp = { 'status': 1, 'message': 'Usage: logout ​<user>​' }
            else:       
                #check whether USER.logined = 0
                if LoginStatus(cursor, second) == 0:
                    resp = Response().notlogin
                else:
                    cursor.execute('UPDATE "USER" SET logined = 0 WHERE token = ?', (second, ) )
                    resp = Response().bye

    elif cmd == 'invite':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 3:
                resp = { 'status': 1, 'message': 'Usage: invite ​<user>​ ​<id>' }
            else:
                #check whether USER.logined = 0
                if LoginStatus(cursor, second) == 0:
                    resp = Response().notlogin
                else:
                    # <id> you invite doesn't exist
                    if USERid_exist(cursor, third) == 0:
                        resp = Response().notexist
                        resp['message'] = ('%s does not exist' %third)
                    else:
                        haverelation = False

                        if second == GetToken(cursor, third):
                            haverelation = True
                            resp = Response().yourself
                        else:
                            # <token> exist in SOCIAL
                            if Social_exist(cursor, second) == 1:
                                for row in GetSocial(cursor, second):
                                    if row[1] == third:
                                        haverelation = True
                                        resp = Response().otherinviteyou
                                        resp['message'] = ('%s has invited you' %third)
                                    if row[2] == third:
                                        haverelation = True
                                        resp = Response().isfriend
                                        resp['message'] = ('%s is already your friend' %third)
                            # <id> exist in SOCIAL
                            if Social_exist(cursor, GetToken(cursor, third)) == 1:
                                for row in GetSocial(cursor, GetToken(cursor, third)):
                                    if row[1] == GetId(cursor, second):
                                        haverelation = True
                                        resp = Response().haveinvite
                                    if row[2] == GetId(cursor, second):
                                        haverelation = True
                                        resp = Response().isfriend
                                        resp['message'] = ('%s is already your friend' %third)
                            if haverelation == False:
                                cursor.execute('INSERT INTO "SOCIAL" (token, who_invite_you) \
                                                VALUES (?, ?)', (GetToken(cursor, third), GetId(cursor, second) ) )
                                resp = Response().success

    elif cmd == 'list-invite':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 2:
                resp = { 'status': 1, 'message': 'Usage: list-invite ​<user>' }
            else:
                #check whether USER.logined = 0
                if LoginStatus(cursor, second) == 0:
                    resp = Response().notlogin
                else:
                    resp = Response().listinvite
                    array = []
                    if Social_exist(cursor, second) == 1:  
                        for row in GetSocial(cursor, second):
                            if row[1] != None:
                                array.append(row[1])
                    resp['invite'] = array

    elif cmd == 'accept-invite':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 3:
                resp = { 'status': 1, 'message': 'Usage: accept-invite ​<user>​ ​<id>​' }
            else:
                #check whether USER.logined = 0
                if LoginStatus(cursor, second) == 0:
                    resp = Response().notlogin
                else:
                    #flag: check whether <id> invite you
                    notinviteyou = True

                    if Social_exist(cursor, second) == 1:
                        #create 'cur' to avoid 'cursor' change because of executing another SQL query
                        #create a whoinvite list
                        cur = GetSocial(cursor, second)
                        whoinvite = []
                        for row in cur:
                            whoinvite.append(row[1])

                        for i in range(len(whoinvite)):
                            if whoinvite[i] == third:
                                cursor.execute('INSERT INTO "SOCIAL" (token, friend) \
                                                VALUES (?, ?)', (second, third ) )
                                cursor.execute('INSERT INTO "SOCIAL" (token, friend) \
                                                VALUES (?, ?)', (GetToken(cursor, third), GetId(cursor, second) ) )
                                cursor.execute('DELETE FROM "SOCIAL" WHERE token = ? AND who_invite_you = ?', (second, third) )
                                resp = Response().success
                                #<id> really invite you
                                notinviteyou = False
                    if notinviteyou == True:
                            resp = Response().notinviteyou
                            resp['message'] = ('%s did not invite you' %third)
    
    elif cmd == 'list-friend':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 2:
                resp = { 'status': 1, 'message': 'Usage: list-friend ​<user>' }
            else:
                #check whether USER.logined = 0
                if LoginStatus(cursor, second) == 0:
                    resp = Response().notlogin
                else:
                    resp = Response().listfriend
                    array = []
                    if Social_exist(cursor, second) == 1:  
                        for row in GetSocial(cursor, second):
                            if row[2] != None:
                                array.append(row[2])
                    resp['friend'] = array    

    elif cmd == 'post':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) < 3:
                resp = { 'status': 1, 'message': 'Usage: post ​<user>​ ​<message>' }
            else:
                #check whether USER.logined = 0
                if LoginStatus(cursor, second) == 0:
                    resp = Response().notlogin
                else:
                    if Social_exist(cursor, second) == 1:
                        #create 'cur' to avoid 'cursor' change because of executing another SQL query
                        #create a friend list
                        cur = GetSocial(cursor, second)
                        friend = []
                        for row in cur:
                            friend.append(row[2])

                        for Friend_No in range(len(friend)):
                            # <token> truly have a friend
                            if friend[Friend_No] != None:
                                msg = ''
                                for i in range(len(third)):
                                    msg = msg + third[i]
                                    if i != len(third)-1:
                                        msg = msg + ' '

                                cursor.execute('INSERT INTO "SOCIAL" (token, post, whopost) \
                                                VALUES (?, ?, ?)', (GetToken(cursor, friend[Friend_No]), msg, GetId(cursor, second) ) )                           
                    resp = Response().success

    elif cmd == 'receive-post':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 2:
                resp = { 'status': 1, 'message': 'Usage: receive-post ​<user>' }
            else:
                #check whether USER.logined = 0
                if LoginStatus(cursor, second) == 0:
                    resp = Response().notlogin
                else:
                    resp = Response().recvpost
                    array = []
                    if Social_exist(cursor, second) == 1:  
                        for row in GetSocial(cursor, second):
                            po = {'id':'' , 'message':'' }
                            if row[3] != None:
                                po['id'] = row[4]
                                po['message'] = row[3]
                                array.append(po)
                    resp['post'] = array


    # Message-Broker: STOMP.send()
    elif cmd == 'send':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) < 4:
                resp = { 'status': 1, 'message': 'Usage: send <user> <friend> <message>' }
            else:
                # <friend> you send doesn't exist
                if USERid_exist(cursor, third) == 0:
                    resp = Response().notexist
                    resp['message'] = 'No such user exist'
                # check whether RECEIVER.logined = 0
                if USERid_exist(cursor, third) == 1:
                    if LoginStatus(cursor, GetToken(cursor, third)) == 0:
                        resp = Response().notonline
                        resp['message'] = ('%s is not online' %third)
                    else:
                        # check whether <friend> is <token>'s friend
                        friend_check = False
                        # <token> exist in SOCIAL
                        if Social_exist(cursor, second) == 1:
                            for row in GetSocial(cursor, second):
                                if row[2] == third:
                                    friend_check = True
                                    break
                        if friend_check == True:
                            resp = Response().success
                            # send message to ActiveMQ server
                            # msg = '<SENDER> message', <SENDER> implies who send this message
                            msg = GetId(cursor, second) + ' '
                            for i in range(len(fourth)):
                                msg = msg + fourth[i]
                                if i != len(fourth)-1:
                                    msg = msg + ' '
                            # Stomp.send()
                            conn = stomp.Connection10([('localhost',61613)])
                            conn.start()
                            conn.connect()
                            conn.send(body=msg, destination=third)
                        else:
                            resp = Response().notyourfriend
                            resp['message'] = ('%s is not your friend' %third)

    elif cmd == 'create-group':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 3:
                resp = { 'status': 1, 'message': 'Usage: create-group <user> <group>' }
            else:
                havegroup = False
                for row in GetAllGroup(cursor):
                    if row[1] == third:
                        havegroup = True
                        resp = Response().existgroup
                        resp['message'] = ('%s already exist' %third) 
                if havegroup == False:
                    cursor.execute('INSERT INTO "GROUP" (token, "group") \
                                    VALUES (?, ?)', (second, third) )
                    resp = Response().success

    elif cmd == 'list-group':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 2:
                resp = { 'status': 1, 'message': 'Usage: list-group ​<user>' }
            else:
                resp = Response().listallgroup
                array = []
                for row in GetAllGroup(cursor):
                    if row[1] != None and row[1] not in array:
                        array.append(row[1])
                resp['allgroup'] = array

    elif cmd == 'list-joined':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 2:
                resp = { 'status': 1, 'message': 'Usage: list-joined ​<user>' }
            else:
                resp = Response().listjoinedgroup
                array = []
                for row in GetJoinedGroup(cursor, second):
                    if row[1] != None and row[1] not in array:
                        array.append(row[1])
                resp['joinedgroup'] = array

    elif cmd == 'join-group':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) != 3:
                resp = { 'status': 1, 'message': 'Usage: join-group <user> <group>' }
            else:
                #check whether GROUP.group already exists 
                cursor.execute('SELECT EXISTS (SELECT * FROM "GROUP" WHERE "group" = ?)', (third,) )
                exist = cursor.fetchone()

                if exist[0] == 0:
                    resp = Response().notexist
                    resp['message'] = ('%s does not exist' %third)
                else:
                    #check whether token has joined to the group
                    cursor.execute('SELECT EXISTS (SELECT * FROM "GROUP" WHERE token = ? AND "group" = ?)', (second, third) )
                    joined = cursor.fetchone()

                    if joined[0] == 1:
                        resp = Response().ismember
                        resp['message'] = ('Already a member of %s' %third)
                    #INSERT (token, group)
                    else:
                        cursor.execute('INSERT INTO "GROUP" (token, "group") \
                                        VALUES (?, ?)', (second, third) )
                        resp = Response().success

    elif cmd == 'send-group':
        if USERtoken_exist(cursor, second) == 0:
            resp = Response().notlogin
        else:
            #USAGE_error
            if len( data.split(' ') ) < 4:
                print(second)
                resp = { 'status': 1, 'message': 'Usage: send-group <user> <group> <message>' }
            else:
                #check whether <group> already exists 
                cursor.execute('SELECT EXISTS (SELECT * FROM "GROUP" WHERE "group" = ?)', (third,) )
                exist = cursor.fetchone()

                if exist[0] == 0:
                    resp = Response().notexist
                    resp['message'] = 'No such group exist'
                else:
                    # check whether <token> is a member of <group>
                    if GROUP_token_exist(cursor, second) == 0:
                        resp =  Response().notmember
                        resp['message'] = ('You are not the member of %s' %third)
                    else:
                        gr_cursor = db.cursor()
                        for row in GetAllGroup(gr_cursor):
                            #[@DEBUG] print(row)
                            # if Group.group == <group>
                            if row[1] == third:
                                '''[debug]
                                print(row[0])
                                print(third)
                                print('--------')
                                '''
                                # if Group.token(the members in <group>) are logined
                                print(LoginStatus(cursor, row[0]))
                                if LoginStatus(cursor, row[0]) == 1:                                    
                                    # send message to ActiveMQ server
                                    # msg = '<SENDER>&<GROUP> message', <SENDER>: message from who / <GROUP>: message from which group
                                    msg = GetId(cursor, second) + '&' + third + ' '
                                    for i in range(len(fourth)):
                                        msg = msg + fourth[i]
                                        if i != len(fourth)-1:
                                            msg = msg + ' '
                                    # Stomp.send()
                                    conn = stomp.Connection10([('localhost',61613)])
                                    conn.start()
                                    conn.connect()
                                    conn.send(body=msg, destination='/topic/'+third)
                                    # send to topic, meaning that only 1 time is ok to let all consumer subscribe
                                    break
                        resp = Response().success
    #Exception:::::Unknown command
    else:
        resp = {'status': 1, 'message': 'Unknown command %s' %cmd}

    '''debug
    elif cmd == 'show_SOCIAL':
        cursor.execute('SELECT * FROM "SOCIAL"')
        sh = db.cursor()
        for row in cursor:
            print('id=%s' %GetId(sh, row[0]) )
            print('who_invite_you=%s' %row[1])
            print('friend=%s' %row[2])
            print('post=%s' %row[3])
            print('whopost=%s' %row[4])
            print()
        resp = Response().success
    elif cmd == 'show_USER':
        cursor.execute('SELECT * FROM "USER"')
        for row in cursor:
            print('id=%s' %row[0] )
            print('pw=%s' %row[1])
            print('token=%s' %row[2])
            print('logined=%d' %row[3]) 
            print()
        resp = Response().success
    '''

    #send message to client.py
    sock.send(json.dumps(resp).encode())

    #close socket
    sock.close()
    print('connection from %s:%s closed.' %addr)

    #commit & close DB
    db.commit()
    db.close()

if __name__ == '__main__':
    #create table in DB
    db = sqlite3.connect('userinfo.db')
    cursor = db.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS "USER" (id VARCHAR(30) PRIMARY KEY, pw VARCHAR(30), token VARCHAR(50), logined INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS "SOCIAL" (token VARCHAR(50), who_invite_you VARCHAR(50), friend VARCHAR(50), post VARCHAR(100), whopost VARCHAR(50), pri_key INTEGER PRIMARY KEY NULL )')
    cursor.execute('CREATE TABLE IF NOT EXISTS "GROUP" (token VARCHAR(50), "group" VARCHAR(50), pri_key INTEGER PRIMARY KEY NULL )')
    db.commit()
    db.close()

    #socket initialization
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)

    #bind to argv[1], argv[2]
    if len(sys.argv) != 3:
        print('arguments error')
        exit(1)
    else:
        HOST = sys.argv[1]
        PORT = int(sys.argv[2])
    s.bind((HOST, PORT))

    #listen
    s.listen(5)
    print('waiting for connection')

    while True:
        sock, addr = s.accept()
        t = threading.Thread(target=TCP, args=(sock, addr))
        t.start()
