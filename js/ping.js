var SleepTime = 30, DeltaTime = 300000;
var S = new ActiveXObject("WScript.Shell"), fso = new ActiveXObject("Scripting.FileSystemObject"), Args = WSH.Arguments;
var Adr, IP, wmi, i, e, s, PrevS = 0, msg, t, HostIsUnreachable, count = 0;
if(Args.Length != 1)WScript.Quit(-1); Adr = Args.item(0);
if(fso.GetFileName(WSH.FullName).toLowerCase() == "wscript.exe")S.Run("cmd.exe /k cscript " + WSH.ScriptName + " " + Adr,1)
else{fso = null; wmi = GetObject("winmgmts:{impersonationLevel=impersonate}!\\\\.\\root\\cimv2");
    while(true){e = new Enumerator(wmi.ExecQuery("Select StatusCode,ResponseTime" + (IP?"":",ProtocolAddress")+
        " from Win32_PingStatus where Address = '" + (IP?IP:Adr) + "'"));
        for(;!e.atEnd();e.moveNext())if((s = (i = e.item()).StatusCode) == 0 || s != PrevS){PrevS = s; HostIsUnreachable = true; switch(s){
            case  null: msg = "для '" + Adr + "' невозможно получить ip адрес."; break;
            case     0: if(!IP)IP = i.ProtocolAddress; msg = (IP?IP:Adr) + " =" + i.ResponseTime + " мс."; HostIsUnreachable = false; count = 0; break;
            case 11002: msg = "Заданная сеть недоступна."; IP = 0; break;
            case 11003: msg = "Хост недоступен."; IP = 0; break;
            case 11010: msg = "Превышен интервал ожидания."; IP = 0; break;
            case 11050: msg = "Общая ошибка (плохо сформированный пакет)."; IP = 0; break;
            default: IP = 0; msg = "Ошибка " + s;
            }WSH.echo(new Date().toLocaleTimeString() + ": " + msg);
            if(HostIsUnreachable && !count--){WSH.echo("Хост недоступен, запуск: " + (cmd_name = Adr + ".cmd")); S.Run("cmd.exe /k " + cmd_name, 1)}
        }
        t = new Date();
        for(i=SleepTime;i;i--)with(WScript)with(StdOut){Write(s=new Date().toLocaleTimeString()+": "+i);Sleep(1000);Write("\b\b  \r")}
        IP=((new Date()-t)<DeltaTime?IP:0);
    }
}