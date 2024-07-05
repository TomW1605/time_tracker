// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: red; icon-glyph: server;

var data = args.shortcutParameter
var url = args.urls[0]

var request = new Request(url)

request.timeoutInterval = 5;
request.method = "post";
request.body = JSON.stringify(data);
request.headers = {"Content-Type":"application/json"}

try {
  var json = await request.loadJSON()
  console.log(request.response.statusCode)
  console.log(json)

  return {"statusCode": request.response.statusCode,
          "body": json}
}
catch(err) {
  console.log(err.name)
  console.log(err.message)
  if (err.message=="The request timed out.") {
    var status_code = "408"
  } else {
    var status_code = request.response.statusCode
  }

  return {"statusCode": status_code,
          "body": ""}
}