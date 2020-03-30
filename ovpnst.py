from datetime import datetime
import getpass
import os
from os import listdir
from os.path import isfile, join
from requests import get
import speedtest
from subprocess import call, PIPE, Popen
import time
import urllib.request

# Get path to running script
rp = os.path.realpath(__file__).strip(__file__)


# Determine download/upload speed
# [String] f: filename
# [Int] t: type of speedtest
# [List] return: List with detected speeds
def getTimes(f, t):
    threads = None
    dlS = ulS = False

    if t == 3:
        print('Testing download...')
        dlS = st.download(threads=threads)
        print('Testing upload...')
        ulS = st.upload(threads=threads)
    elif t == 1:
        print('Testing download...')
        dlS = st.download(threads=threads)
    elif t == 2:
        print('Testing upload...')
        ulS = st.upload(threads=threads)
    else:
        return False

    return [dlS, ulS]


# Calculate bits to MBytes
# [Float] bits
# [String] return: Readable string
def b2MB(bits):
    bits = bits * 0.00000011921
    return '%.2f' % bits + ' MB/s'


# Write results file header
def writeResultsHeader():
    rf = open(rp + 'results.txt', 'a')
    rf.write('\n_________________ ' + str(datetime.now())
             + ' _________________')
    rf.write('\nFilename..............................')
    rf.write('....Download')
    rf.write('......Upload')
    rf.close()


# Write speedtest results to file
# [string] f: Config file name
# [List] times: Download/Upload times
def writeResults(f, times):
    rf = open(rp + 'results.txt', 'a')
    rf.write('\n' + f)
    i = 0

    # Check if filename is too long
    if len(f) > 38:
        f = f[:38]

    # Add spacer
    while i < 40 - len(f):
        rf.write('.')
        i += 1

    # Write download time
    if times[0]:
        op = b2MB(times[0])
        i = 1
        while i < 11 - len(op):
            rf.write('.')
            i += 1
        rf.write(op)
    else:
        rf.write('.......N/A')

    # Add spacer
    rf.write('..')

    # Write upload time
    if times[1]:
        op = b2MB(times[1])
        i = 1
        while i < 11 - len(op):
            rf.write('.')
            i += 1
        rf.write(op)
    else:
        rf.write('.......N/A')

    rf.close()


# Check if internet connection works
def checkInternetConnection():
    try:
        urllib.request.urlopen('https://google.com')
    except Exception:
        return False
    else:
        return True


# Check if given file is an openvpn config file
# [string] f: full path to file
def fileIsConfig(f):
    hasClientLine = False
    hasRemoteLine = False
    file = open(f, 'r')
    for l in file.readlines():
        if l.startswith('remote'):
            hasRemoteLine = True
        elif l.startswith('client'):
            hasClientLine = True
    file.close()

    if hasRemoteLine and hasClientLine:
        return True
    else:
        return False


# Get openvpn configuration files and store them seperatly
# [string] path: path to config folder
# [string] prefix: file prefix that files need to start with
def getConfigFiles(path, prefix):
    # Store filenames
    if prefix:
        configFiles = [f for f in listdir(path) if isfile(join(path, f))
                       and f.startswith(prefix)
                       and not f.startswith('.')]
    else:
        configFiles = [f for f in listdir(path) if isfile(join(path, f))
                       and not f.startswith('.')]

    # Check if any file isn't an openvpn config file
    for f in configFiles:
        isConfig = fileIsConfig(path + f)

        # Remove faulty file
        if not isConfig:
            print('\n' + f + ' does not look like a proper config file. ' +
                  'Removing...')
            configFiles.remove(f)

    # Check if there are config file to use
    if len(configFiles) < 1:
        print('\nThere weren\'t any configuration files to use. ' +
              'Starting over...')
        return False

    print('\n' + str(len(configFiles)) + ' File(s) found')

    # Copy files for temporary use
    print('Copying files...\n')
    for f in configFiles:
        call(['cp', path + f, rp + 'ovpn_config_files'])

    return configFiles


# Create authentication file
# [string] uname: Username
# [string] pwd: Password
def createAuthConfig(uname, pwd):
    f = open(rp + 'user_auth.conf', 'w')
    f.write(uname + '\n' + pwd)
    f.close()

# Ask in which way the servers are beeing tested
print('What do you want to test?')
print('(1) Only download')
print('(2) Only upload')
print('(3) Both download and upload')
tests = 0
while tests < 1 or tests > 3:
    try:
        tests = int(input('Please enter: '))
    except ValueError:
        print('Please enter a valid number.')

# Speedtest API settings
print('Configuring speedtest parameters...')
st = speedtest.Speedtest()
servers = []
st.get_servers(servers)
st.get_best_server()

# Create temporary config directory
tmpConfigDir = 'ovpn_config_files'
call(['mkdir', tmpConfigDir], stdout=PIPE, stderr=PIPE)
call(['rm', tmpConfigDir, '/*'], stdout=PIPE, stderr=PIPE)

# Get sudo user privilege (Using call to get the sudo prompt)
print('\nStopping all openvpn connections...\n')
print('Warning: You need sudo privileges to start openvpn.')
call(['sudo', 'killall', 'openvpn'], stderr=PIPE)

# Ask for path to search for config files
configFiles = False
while not configFiles:
    path = input('\nPath for openvpn config files: ')
    if path.startswith('~'):
        path = '/home/' + getpass.getuser() + path[1:]
    if path[-1:] != '/':
        path += '/'

    # Get file prefix
    np = input('\nDo you want to use a file prefix to only ' +
               'use files that start with a certain string? [y/N]: ')

    if np.lower() == 'n' or np == '':
        prefix = ''
    else:
        prefix = input('Prefix: ')

    configFiles = getConfigFiles(path, prefix)

# Ask for vpn server authentication if needed
na = input('Do you need authentication for your vpn server? [Y/n]: ')
if na.lower() == 'y' or na == '':
    print('Warning: This tool creates a temporary configuration file ' +
          'for entering your username and password')

    # Set flag
    usesAuth = True

    # Ask for credentials
    uname = input('Username: ')
    pwd = getpass.getpass('Password: ')

    createAuthConfig(uname, pwd)
else:
    usesAuth = False

# Get current public IP
ip = get('https://api.ipify.org').text

# Write new entry for results.txt
writeResultsHeader()

# Ask for user input to start test
input('\nPress ENTER to start testing (ET: ' +
      str(len(configFiles) * 15) + 'sec)...')

authCorr = False

# Connect to vpn server
for f in configFiles:

    print('\nConnecting to ' + f + '...')

    # Add user authentication file to config file
    if usesAuth:
        tmpConfigFile = open(rp + tmpConfigDir + '/' + f, 'a')
        tmpConfigFile.write('\nauth-user-pass ' + rp + 'user_auth.conf')
        tmpConfigFile.close()

    # Start nordvpn service
    Popen('sudo openvpn ' + rp + tmpConfigDir + '/' + f, shell=True,
          stdin=None, stdout=PIPE, stderr=PIPE, close_fds=True)

    newIP = ip
    internetWorks = isError = False
    i = errCocde  = 0

    # Check if connected successfully to server
    while (newIP == ip or not internetWorks):
        time.sleep(3)
        internetWorks = checkInternetConnection()
        if not internetWorks:
            continue
        try:
            newIP = get('https://api.ipify.org').text
        except:
            isError = True
            errCode = 1
            break

        # Set error after 18 seconds
        i += 1
        if i >= 6:
            isError = True
            errCode = 2
            break

    # Cancel progress if vpn connection won't work
    if isError:
        em = 'Connection failed (' + str(errCode) + '). Skipping...'
        if usesAuth and not authCorr:
            em += '\nMake sure your username and password are correct.'
        print(em)

        # Stop any openvpn process
        call(['sudo', 'killall', 'openvpn'], stderr=PIPE)
        continue

    # Var for checking if any connection could already be established
    authCorr = True

    # Get download speed
    times = getTimes(f, tests)
    if times[0]:
        print('-> Download: ' + b2MB(times[0]))
    if times[1]:
        print('-> Upload: ' + b2MB(times[1]))

    writeResults(f, times)

    # Stop any openvpn process
    call(['sudo', 'killall', 'openvpn'], stderr=PIPE)
    time.sleep(1)


print('\nResults were written into the results.txt.')

# Clean up
call(['rm', rp + 'user_auth.conf'])
call(['rm', '-rf', rp + 'ovpn_config_files'])
