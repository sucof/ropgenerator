# -*- coding:utf-8 -*- 
# Load module: load a binary and extract gadgets from it 

import sys
import os
import subprocess
import io
from base64 import b16decode
from random import shuffle, random, randrange, Random
from magic import from_file
from datetime import datetime

from ropgenerator.core.IO import *
from ropgenerator.core.Architecture import *
from ropgenerator.core.Symbolic import raw_to_IRBlock
from ropgenerator.core.Gadget import *
from ropgenerator.core.Database import *
from ropgenerator.core.ChainingEngine import *

# Command options
OPTION_ARCH = '--arch'
OPTION_ARCH_SHORT = '-a'
OPTION_HELP = '--help'
OPTION_HELP_SHORT = '-h'
OPTION_ROPGADGET_OPTIONS = '--ropgadget-opts'
OPTION_ROPGADGET_OPTIONS_SHORT = '-r'

# Help for the load command
helpStr = banner([str_bold("'load' command"),
    str_special("(Load gadgets from a binary file)")])
helpStr += "\n\n\t"+str_bold("Usage")+":\tload [OPTIONS] <filename>"
helpStr += "\n\n\t"+str_bold("Options")+":"
helpStr += "\n\t\t"+str_special(OPTION_ARCH_SHORT)+","+str_special(OPTION_ARCH)+\
" <arch>"+"\t\tmanualy specify architecture.\n\t\t\t\t\t\tAvailable: 'X86', 'X64'"
helpStr += '\n\n\t\t'+str_special(OPTION_ROPGADGET_OPTIONS_SHORT)+","+str_special(OPTION_ROPGADGET_OPTIONS)+\
" <opts>"+"\textra options for ROPgadget.\n\t\t\t\t\t\t<opts> must be a list of\n\t\t\t\t\t\toptions between ''"+\
"\n\t\t\t\t\t\te.g: \'-depth 4\'"
helpStr += "\n\n\t"+str_bold("Examples")+":\n\t\tload /bin/ls \n\t\tload ../test/vuln_prog \n\t\tload -r '-norop' /bin/tar"


def print_help():
    print(helpStr)

def getPlatformInfo(filename):
    """
    Checks the binary type of the file
    Precondition: the file exists ! 
    
    Effects: set the Arch.currentBinType variable
    Return : the corresponding architecture 
    """
    INTEL_strings = ["x86", "x86-64", "X86", "X86-64", "Intel", "80386"]
    ELF32_strings = ["ELF 32-bit"]
    ELF64_strings = ["ELF 64-bit"]
    PE32_strings = ["PE32 "]
    PE64_strings = ["PE32+"]
    
    output = from_file(os.path.realpath(filename))
    if( [sub for sub in INTEL_strings if sub in output]):
        if( [sub for sub in ELF32_strings if sub in output]):
            notify("ELF 32-bits detected")
            set_bin_type(BinType.BIN_X86_ELF)
            return ArchType.ARCH_X86
        elif( [sub for sub in ELF64_strings if sub in output]):
            notify("ELF 64-bits detected")
            set_bin_type(BinType.BIN_X64_ELF)
            return ArchType.ARCH_X64
        elif( [sub for sub in PE32_strings if sub in output]):
            notify("PE 32-bits detected")
            set_bin_type(BinType.BIN_X86_PE)
            return ArchType.ARCH_X86
        elif( [sub for sub in PE64_strings if sub in output]):
            notify("PE 64-bits detected")
            set_bin_type(BinType.BIN_X64_PE)
            return ArchType.ARCH_X64
        else:
            notify("Unknown binary type")
            set_bin_type(BinType.BIN_UNKNOWN)
            return None
    else:
        return None 

def get_gadgets(filename, extra_args=''):
    """
    Returns a list of gadgets extracted from a file 
    Precondition: the file exists 
    
    Returns
    -------
    list of pairs (addr, asm) if succesful
    None if failure 
    """    
   
    ropgadget = "ROPgadget"
    cmd_string = ''
    try:
        cmd = [ropgadget,"--binary", filename, "--dump", "--all"]
        if( extra_args ):
            cmd += extra_args.split(" ")
        cmd_string = " ".join(cmd)
        notify("Executing ROPgadget as: " + cmd_string)
        (outdata, errdata) = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    except Exception as e:
        error("Could not execute '"+ cmd_string + "'")
        print("\tException message: " + str(e))
        return None

    # Check if error
    errs = io.StringIO(errdata.decode("ascii"))
    l = errs.readline()
    while( l ):
        if( 'error:' in l):
            error("Could not execute '"+ cmd_string + "'")
            print("\tError message: " + str_special(l.split('error:')[1]))
            return None
        l = errs.readline()

    # Get the gadget list 
    # Pairs (address, raw_asm)
    first = True
    count = 0
    res = []
    outs = io.StringIO(outdata.decode("ascii"))
    l = outs.readline()
    while( l ):
        if('0x' in l):
            arr = l.split(' ')
            addr = arr[0]
            raw = b16decode(arr[-1].upper().strip())
            res.append((int(addr,16), raw))
            count += 1 
        l = outs.readline()
    notify("Gadgets generated: %d" % (count))
    return res
    
def load(args):
    global helpStr
    global loaded
    global biggest_gadget_addr
    # Parse arguments and filename 
    filename = None
    user_arch = None
    biggest_gadget_addr = 0
    ropgadget_options = ''
    
    i = 0
    seenArch = False
    seenRopgadget = False
    
    if( not args ):
        print(helpStr)
        return 

    while i < len(args):
        if( args[i] in [OPTION_ARCH, OPTION_ARCH_SHORT] ):
            if( seenArch ):
                error("Option {} can be used only one time"\
                .format(args[i]))
                return 
            seenArch = True
            if( i+1 == len(args)):
                error("Missing argument after {}.\n\tType 'load -h' for help"\
                .format(args[i]))
                return 
            elif( args[i+1] == OPTION_ARCH_NAMES['X86'] ):
                user_arch = ArchType.ARCH_X86
            elif( args[i+1] == OPTION_ARCH_NAMES['X64'] ):
                user_arch = ArchType.ARCH_X64
            else:
                error("Unknown architecture: {}".format(args[i+1]))
                return 
            i += 2
        elif( args[i] in [OPTION_HELP, OPTION_HELP_SHORT] ):
            print(helpStr)
            return 
        elif( args[i] in [OPTION_ROPGADGET_OPTIONS, OPTION_ROPGADGET_OPTIONS_SHORT]):
            if( seenRopgadget ):
                error("Option {} can be used only one time"\
                .format(args[i]))
                return 
            if( i+1 == len(args)):
                error("Missing argument after {}.\n\tType 'load -h' for help"\
                .format(args[i]))
                return 
            seenRopgadget = True
            (index, ropgadget_options) = parse_ropgadget_options(args[i+1:])
            if( index == -1 ):
                error(ropgadget_options)
                return
            i += index+1
        else:
            filename = args[i]
            break
    if( not filename ):
        error("Missing filename.\n\tType 'load help' for help")
        return 
    
    # Test if the file exists 
    if( not os.path.isfile(filename)):
        error("Error. Could not find file '{}'".format(filename))
        return 
        
    print('')
    info(str_bold("Scanning file")+ " '" + filename + "'\n")
    
    # # Cleaning the data structures
    # initDB()
    # Arch.reinit()
    
    # # Get architecture and OS info  
    arch = getPlatformInfo(filename)
    if(arch == user_arch == None):
        error("Error. Could not determine architecture")
        return 
    elif( arch and user_arch and (arch != user_arch) ):
        error("Error. Conflicting architectures")
        print("\tUser supplied: " + user_arch.name)
        print("\tFound: " + arch.name)
        return 
    elif( arch ):
        set_arch(arch)
    else:
        set_arch(user_arch)
        
    # # Init the binary scanner
    # initScanner(filename)
    
    # # Extract the gadget list 
    gadget_list = get_gadgets(filename, ropgadget_options)
    if( not gadget_list ):
        return 
        
    # Analyse gadgets 
    try: 
        init_gadget_db();
        start_time = datetime.now()
        dup = dict()
        count = 0
        total = 0
        print('')
        info(str_bold("Analyzing gadgets\n"))
        for( addr, raw) in gadget_list:
            total += 1
            charging_bar(len(gadget_list), total)
            if( raw in dup ):
                count += 1
                continue
            dup[raw] = True
            (irblock, asm_instr_list) = raw_to_IRBlock(raw)
            if( not irblock is None ):
                # Create C++ object 
                gadget = Gadget(irblock)
                # Set different strings 
                asm_str = '; '.join(str(i) for i in asm_instr_list)
                gadget.set_asm_str(asm_str)
                gadget.set_hex_str("\\x" + '\\x'.join("{:02x}".format(c) for c in raw))
                # Manually check for call (ugly but no other solution for now)
                if( str(asm_instr_list[-1]).split(" ")[0] == "call" and
                    gadget.ret_type() == RetType.JMP):
                    gadget.set_ret_type(RetType.CALL)
                # Manually detect false positives for ret (e.g pop rax; jmp rax)
                elif( str(asm_instr_list[-1]).split(" ")[0] == "jmp" and
                    gadget.ret_type() == RetType.RET):
                    gadget.set_ret_type(RetType.UNKNOWN)
                # Add address
                gadget.add_address(addr)
                biggest_gadget_addr = max(addr, biggest_gadget_addr)
                # Add instruction count
                gadget.set_nb_instr(len(asm_instr_list))
                gadget.set_nb_instr_ir(irblock.nb_instr())
                # Add to database 
                gadget_db_add(gadget)
    except:
        print("DEBUG !!! Unexpected exception happened !! :O")
        
    end_time = datetime.now()
    
    notify("Gadgets analyzed : " + str(total))
    notify("Duplicates: " + str(count))
    notify("Database entries created: " + str(gadget_db_entries_count()))
    notify("Computation time : " + str(end_time-start_time))
    
    # # Init engine 
    # initEngine()
    loaded = True


def parse_ropgadget_options(args):
    """
    args is a list of arguments, starting by the first ropgadget argument, 
    function returns a tuple (index, arg_string) with index being the index 
    of the first argument comming after the ropgadet arguments and arg_string
    the string with all args to ropgadget
    returns (-1, error_msg) if fail
    """
    ropgadget_options = ''
    i=0
    # Read the argments
    if( args[i][0] != "'" ):
        return (-1, "ROPgadget options must be given between '' ")
    if( args[i][-1] == "'" and len(args[i]) != 1):
        ropgadget_options += args[i][1:-1]
    else:
        ropgadget_options += args[i][1:]
        i += 1
        closed_ok = False
        while( i < len(args)):
            if( args[i][0] != "'" ):
                if( args[i][-1] == "'"):
                    ropgadget_options += " " + args[i][0:-1]
                    closed_ok = True
                    break
                elif( "'" in args[i] ):
                    return(-1, "ROPgadget options: You must leave a space after the closing '")
                else:
                    ropgadget_options += " " + args[i]
            else:
                if( len(args[i]) > 1):
                    return(-1, "ROPgadget options: You must leave a space after the closing '")
                else:
                    closed_ok = True
                    break
            i += 1
        if( not closed_ok ):
            return (-1, "ROPgadget options: missing closing \'")
    return (i+1, ropgadget_options)


###################################
# Module wide
loaded = False
biggest_gadget_addr = 0

def loaded_binary():
    global loaded
    return loaded

def biggest_gadget_address():
    global biggest_gadget_addr
    return biggest_gadget_addr    

    
