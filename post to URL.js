// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: red; icon-glyph: server;

var data = args.shortcutParameter
var url = args.urls[0]

var request = new Request(url)

request.method = "post";
request.body = JSON.stringify(data);
request.headers = {"Content-Type":"application/json"}

var json = await request.loadJSON()
console.log(request.response.statusCode)
console.log(json)

return {
        "statusCode": request.response.statusCode,
        "body": json
}