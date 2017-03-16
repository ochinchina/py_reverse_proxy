# about this project
this project implements a very simple reverse tcp/http proxy with json confiugration file.

# configuration file

configuration file looks like:

```json
{
"server1":{
  "listen": "address:port",
  "backends":["backend1_address:port", "backend2_address:port"]
},
"server2":{
  "listen": "address:port",
  "backends":["backend1_address:port", "backend2_address:port"]
}
}
```

# start the reverse proxy

Edit a confiuration with format listed in the section "configuration file" and start the reverse_proxy.py with option "--config":

```shell
$ python reverse_proxy.py --config my_config.json
```

# License

Apache license 2.0
