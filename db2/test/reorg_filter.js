var block = "", include = false, fso = new ActiveXObject("Scripting.FileSystemObject");
var input = fso.OpenTextFile(WScript.Arguments.Item(0), 1, false);
var output = fso.CreateTextFile(WScript.ScriptFullName.replace(/\.js/i, ".txt"), true);
while(!input.AtEndOfStream){
    line = input.ReadLine();
    if(/^reorgchk\s/i.test(line)){
        if(include)output.WriteLine(block);
        block = "";
        include = false;
    }
    block += line + "\n";
    if(/\s([-*]{3}|[-*]{5})\s+$/.test(line))if(/\*/.test(RegExp.$1))include = true;
}
if(include)output.WriteLine(block);
