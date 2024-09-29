var SleepTime=30;
var S=WScript.CreateObject("WScript.Shell"),fso=new ActiveXObject("Scripting.FileSystemObject"),Args=WScript.Arguments,Adr,IP,wmi,i,e,s,PrevS=0,msg;
if(Args.Length!=1)WScript.Quit(-1);Adr=Args.item(0);
if(fso.GetFileName(WScript.FullName).toLowerCase()=="wscript.exe")S.Run("cmd /k cscript "+WScript.ScriptName+" "+Adr,1)
else{	S=null;fso=null;wmi=GetObject("winmgmts:{impersonationLevel=impersonate}!\\\\.\\root\\cimv2");
	while(true){e=new Enumerator(wmi.ExecQuery("Select StatusCode,ResponseTime"+(IP?"":",ProtocolAddress")+
		" from Win32_PingStatus where Address = '"+(IP?IP:Adr)+"'"));
		for(;!e.atEnd();e.moveNext())if((s=(i=e.item()).StatusCode)==0||s!=PrevS){PrevS=s;switch(s){
			case  null:msg="для '"+Adr+"' невозможно получить ip адрес.";break;
			case     0:if(!IP)IP=i.ProtocolAddress;msg=(IP?IP:Adr)+" ="+i.ResponseTime+" мс.";break;
			case 11002:msg="Заданная сеть недоступна.";break;
			case 11003:msg="Хост недоступен.";break;
			case 11010:msg="Превышен интервал ожидания.";break;
			default:msg="Ошибка "+s;
			}WScript.echo(new Date().toLocaleTimeString()+": "+msg)
		}
		for(i=SleepTime;i;i--)with(WScript)with(StdOut){Write(s=new Date().toLocaleTimeString()+": "+i);Sleep(1000);Write("\b\b  \r")}
	}
}