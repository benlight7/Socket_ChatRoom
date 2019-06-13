import sys
import socket
import json
import os
import stomp
import threading
import time
#(0)Last Question: 要怎麼避免logout_counter_past_idx與logout_counter_now_idx的race condition問題呢？
#(1)delete有做unsubscibe了嗎？還是因為no such user所以並不會顯示呢？
login_log = []
login_counter_past_idx = -1
login_counter_now_idx = -1
logout_log = []
logout_counter_past_idx = -1
logout_counter_now_idx = -1

#set a flag to terminate the thread
subscribe_thread_stop = False

class Client(object):
    def __init__(self, ip, port):
        try:
            socket.inet_aton(ip)
            if 0 < int(port) < 65535:
                self.ip = ip
                self.port = int(port)
            else:
                raise Exception('Port value should between 1~65535')
            self.cookie = {}
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def run(self):
        while True:
            #debug
            '''
            print('login_log: ' , login_log)
            print('login_counter_now_idx: ' , login_counter_now_idx)
            print('login_counter_past_idx: ' , login_counter_past_idx)
            
            print('logout_log: ' , logout_log)
            print('logout_counter_now_idx: ' , logout_counter_now_idx)
            print('logout_counter_past_idx: ' , logout_counter_past_idx)
            '''
            cmd = sys.stdin.readline()
            if cmd == 'exit' + os.linesep:
                return
            if cmd != os.linesep:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((self.ip, self.port))
                        cmd = self.__attach_token(cmd)
                        s.send(cmd.encode())
                        resp = s.recv(4096).decode()
                        self.__show_result(json.loads(resp), cmd)
                except Exception as e:
                    print(e, file=sys.stderr)

    def __show_result(self, resp, cmd=None):
        if 'message' in resp:
            print(resp['message'])

        if 'invite' in resp:
            if len(resp['invite']) > 0:
                for l in resp['invite']:
                    print(l)
            else:
                print('No invitations')

        if 'friend' in resp:
            if len(resp['friend']) > 0:
                for l in resp['friend']:
                    print(l)
            else:
                print('No friends')

        if 'post' in resp:
            if len(resp['post']) > 0:
                for p in resp['post']:
                    print('{}: {}'.format(p['id'], p['message']))
            else:
                print('No posts')

        if 'allgroup' in resp:
            if len(resp['allgroup']) > 0:
                for ag in resp['allgroup']:
                    print(ag)
            else:
                print('No groups')

        if 'joinedgroup' in resp:
            if len(resp['joinedgroup']) > 0:
                for ag in resp['joinedgroup']:
                    print(ag)
            else:
                print('No groups')

        if cmd:
            command = cmd.split()
            global login_counter_now_idx
            global logout_counter_now_idx
            if resp['status'] == 0 and command[0] == 'login':
                self.cookie[command[1]] = resp['token']
                #login_log[] add new element, command[1] is <id>
                login_log.append(command[1])
                login_counter_now_idx += 1
                #subscribe user's already joined groups 
                login_th_group = threading.Thread(target=ThreadGroup, args=(resp['usergroup'], command[1], None))
                login_th_group.start()
            if resp['status'] == 0 and command[0] == 'logout':
                #logout_log[] add new element, command[1] is <token>, need convert to <id>
                for key in self.cookie:
                    if self.cookie[key] == command[1]:
                        unsub_id_getfrom_token = key
                logout_log.append(unsub_id_getfrom_token)
                self.cookie.pop(unsub_id_getfrom_token)
                logout_counter_now_idx += 1
            if resp['status'] == 0 and (command[0] == 'create-group' or command[0] == 'join-group'):
                 #'create-group' and 'join-group' command[1] is <token>, need convert to <id>
                for key in self.cookie:
                    if self.cookie[key] == command[1]:
                        unsub_id_getfrom_token = key
                create_join_th_group = threading.Thread(target=ThreadGroup, args=([], unsub_id_getfrom_token, command[2]))
                create_join_th_group.start()

    def __attach_token(self, cmd=None):
        if cmd:
            command = cmd.split()
            if len(command) > 1:
                if command[0] != 'register' and command[0] != 'login':
                    if command[1] in self.cookie:
                        command[1] = self.cookie[command[1]]
                    else:
                        command.pop(1)
            return ' '.join(command)
        else:
            return cmd

class MyListener(object):
    def on_error(self, headers, message):
        print('received an error %s' % message)
    def on_message(self, headers, message):
        # divide '<SENDER> message' or '<SENDER>&<GROUP> message' to 'SENDER', 'GROUP', and store in senderID & groupNAME, respectively
        sendgroup = False
        # CONDITION1 'send-group': <SENDER>&<GROUP>
        if '&' in message.split(' ')[0]:
            sendgroup = True
            senderID = message.split(' ')[0].split('&')[0]
            groupNAME = message.split(' ')[0].split('&')[1]
        # CONDITION2 'send': <SENDER> only
        else:
            senderID = message.split(' ')[0]
        # divide '/queue/id' to 'id'(or group) and store into receiverID(or receiverGROUP)
        receiverID = headers['destination'].split('/')[2]
        # divide '<SENDER> message' or '<SENDER>&<GROUP> message' to 'message' and store into msg
        msg = ''
        for i in range(len(message.split(' '))):
            if i != 0:
                msg = msg + message.split(' ')[i]
                if i != len(message.split(' '))-1:
                    msg = msg + ' '
        if sendgroup == True:
            print('<<<%s->GROUP<%s>: %s>>>' %(senderID, receiverID, msg))
        else:
            print('<<<%s->%s: %s>>>' %(senderID, receiverID, msg))

def ThreadGroup(groupArray, username, create_or_join):
    ## Stomp.subscribe()
    conn = stomp.Connection10([('localhost',61613)])
    lst = MyListener()
    conn.set_listener('MyListener', lst)
    conn.start()
    conn.connect()

    if len(groupArray) != 0:
        for gr in groupArray:
            conn.subscribe(destination='/topic/'+gr)
            #[@DEBUG] print('** subscribe group: %s' %gr)

        while(1):
            if len(logout_log) != 0 and username == logout_log[logout_counter_now_idx] and logout_counter_now_idx > logout_counter_past_idx:
                for gr in groupArray:
                    conn.unsubscribe(destination='/topic/'+gr)
                    #[@DEBUG] print('** unsubscribe group: %s' %gr)
                return
            # exit()
            if subscribe_thread_stop == True:
                conn.disconnect()
                return
    else:
        if create_or_join == None:
            return
        else:
            conn.subscribe(destination='/topic/'+create_or_join)
            #[@DEBUG] print('** subscribe group: %s' %create_or_join)
            while(1):
                if len(logout_log) != 0 and username == logout_log[logout_counter_now_idx] and logout_counter_now_idx > logout_counter_past_idx:
                    conn.unsubscribe(destination='/topic/'+create_or_join)
                    #[@DEBUG] print('** unsubscribe group: %s' %create_or_join)
                    return
                # exit()
                if subscribe_thread_stop == True:
                    conn.disconnect()
                    return


def subscribe_function():
    ## Stomp.subscribe()
    conn = stomp.Connection10([('localhost',61613)])
    lst = MyListener()
    conn.set_listener('MyListener', lst)
    conn.start()
    conn.connect()
    
    while(1):
        global login_counter_past_idx
        global logout_counter_past_idx
        # a user login successfully ,which implied that login_log[].len() increased
        if(login_counter_now_idx > login_counter_past_idx):
            conn.subscribe(destination=login_log[login_counter_now_idx])
            #[@DEBUG] print('** subscribe personal: %s' %login_log[login_counter_now_idx])
            login_counter_past_idx += 1
        # a user logout successfully ,which implied that logout_log[].len() increased
        if(logout_counter_now_idx > logout_counter_past_idx):
            # for ThreadGroup() to recognize to unsubscribe user's all groups
            time.sleep(100000/1000000.0)
            
            logout_counter_past_idx += 1
            conn.unsubscribe(destination=logout_log[logout_counter_now_idx])
            #[@DEBUG] print('** unsubscribe personal: %s' %logout_log[logout_counter_now_idx])

        # exit()
        if subscribe_thread_stop == True:
            conn.disconnect()
            return

def launch_client(ip, port):
    c = Client(ip, port)
    c.run()

if __name__ == '__main__':
    if len(sys.argv) == 3:
        # subscribe thread
        t = threading.Thread(target=subscribe_function)
        t.start()
        # client program
        launch_client(sys.argv[1], sys.argv[2])
        # if 'exit' is input by user
        subscribe_thread_stop = True
    else:
        print('Usage: python3 {} IP PORT'.format(sys.argv[0]))
