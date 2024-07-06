// Добавление к имени файла даты модификации и версии файла по формату <Имя>_YYYY-MM-DD(<Версия>).<Расширение>
// Для файлов .ts добавляется дата и время создания по формату YYMMDD-HHMMSS-<имя>.ts

var objShellApp = new ActiveXObject("Shell.Application"), fso = new ActiveXObject("Scripting.FileSystemObject"), fn, s = "";

with(WScript.Arguments)
    for(var i=0; i<length; i++)
        if(fso.FileExists(fn=Item(i)))
            addVersionToFileName(fn);
        else s += "\n" + fn;
if(s)
    WScript.echo("Файл(ы) не найден(ы): "+s);

function addVersionToFileName(fn){
    var f = fso.GetFile(fn), d, e = fso.GetExtensionName(fn);
    fn = f.Name;
    if(e=="ts"){
        if(!fn.match(d=DateTimeString(f)))
            f.Name = d + fn;
        return;
    }
    var ver = getVersion(f), v = ver?"\\("+ver.replace(/\./,"\\.")+"\\)":"";
    if(!fn.match(d=DateString(f)))
        fn = fn.replace(new RegExp((v?"((?:"+v+".*)*":"(")+"\\."+e+")$"), d+"$1");
    if(v&&!fn.match(v))
        fn = fn.replace(new RegExp("\."+e+"$"), "("+ver+")."+e);
    if(fn!=f.Name)
        f.Name = fn;
}

function getVersion(f){
    var i, maxN = 310, objFolder = objShellApp.NameSpace((f.ParentFolder+"\\").replace(/\\+$/,"\\")),
        objItem = objFolder.ParseName(f.Name), versions = new Array(5);
    if(/Версия файла:\s*([\d.]+)/.test(objFolder.GetDetailsOf(objItem,-1)))
        return RegExp.$1;
    for(i=0; i<maxN; i++){
        propName = objFolder.GetDetailsOf(null,i);
        if(/Версия файла/.test(propName))
            versions[0] = objFolder.GetDetailsOf(objItem,i);
        if(/^Описание(?: файла)?$/.test(propName))
            if(/((?:\d+\.)+\d+)/.test(objFolder.GetDetailsOf(objItem,i)))
                 versions[1] = RegExp.$1;
        if(/Версия продукта/.test(propName))
            versions[3] = objFolder.GetDetailsOf(objItem,i);
        if(/Название продукта/.test(propName))
            if(/((?:\d+\.)+\d+)/.test(objFolder.GetDetailsOf(objItem,i)))
                 versions[4] = RegExp.$1;
    }
    if(/Описание файла:[\D]*((?:\d+\.)+\d+)/.test(objFolder.GetDetailsOf(objItem,-1)))
        versions[2] = RegExp.$1;
    for(i=0; i<versions.length; i++)
        if(versions[i])
            return versions[i];
}

function DateString(f){
    var d = new Date(f.DateLastModified);
    return "_" + d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
}

function DateTimeString(f){
    var d = new Date(f.DateCreated);
    return "" + (d.getFullYear() % 100) + ("0" + (d.getMonth() + 1)).slice(-2) + ("0" + d.getDate()).slice(-2) + "-" +
        ("0" + d.getHours()).slice(-2) + ("0" + d.getMinutes()).slice(-2) + ("0" + d.getSeconds()).slice(-2) + "-";
}