server {
        server_name zev.averba.ch;

	root /var/www/zev.averba.ch/html;
        index index.html index.htm index.nginx-debian.html;

        access_log /var/log/nginx/zev.averba.ch.access.log;
        error_log /var/log/nginx/zev.averba.ch.error.log;

        location /create {
            include proxy_params;
            proxy_pass http://unix:/home/averba.ch/averba.ch.sock;
        }

        location /create_page {
            include proxy_params;
            proxy_pass http://unix:/home/averba.ch/averba.ch.sock;
        }

        location /update_page {
            include proxy_params;
            proxy_pass http://unix:/home/averba.ch/averba.ch.sock;
        }

        location /delete_page {
            include proxy_params;
            proxy_pass http://unix:/home/averba.ch/averba.ch.sock;
        }

	if ($request_uri = /index.html) {
	    return 301 https://zev.averba.ch/;
	}
	if ($request_uri = /index) {
	    return 301 https://zev.averba.ch/;
	}

	location / {
	    if ($request_uri ~ ^/(.*)\.html) {
		return 302 /$1;
	    }
	    try_files $uri $uri.html $uri/ =404;
        }


    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/zev.averba.ch/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/zev.averba.ch/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}

server {
    listen 80 default_server;
    server_name _;
    return 301 https://$host$request_uri;
}
server {
    if ($host = zev.averba.ch) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


        server_name zev.averba.ch;
    listen 80;
    return 404; # managed by Certbot


}
