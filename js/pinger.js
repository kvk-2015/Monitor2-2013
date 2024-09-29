var fso=new ActiveXObject("Scripting.FileSystemObject"),Args=WScript.Arguments,S=WScript.CreateObject("WScript.Shell"),sArgs="",cto=0,cun=0,gen=0,str;
with(str=new ActiveXObject("ADODB.Stream")){Type=2;Mode=3}
for(var i=0;i<Args.length;i++)sArgs+=" "+Args.item(i);
if(fso.GetFileName(WScript.FullName).toLowerCase()=="wscript.exe"){
	S.Run("cmd /k cscript "+WScript.ScriptName+" "+sArgs,1);
}else{	var s,oExec=S.Exec("ping "+sArgs);
    while(!oExec.Status){s=DosToWin(oExec.StdOut.ReadLine());
        if(/timed out|Превышен интервал/.test(s))cto++;else cto=0;
        if(/unreach|недоступ/.test(s))cun++;else cun=0;
        if(/gener|общий/i.test(s))gen++;else gen=0;
        if(cto+cun+gen<=3)WScript.echo(new Date().toLocaleTimeString()+": "+s);
    }
}
function DosToWin(s){var r;with(str){Open();Charset="Windows-1251";WriteText(s);Position=0;Charset="cp866";r=ReadText();Close()}return r}
