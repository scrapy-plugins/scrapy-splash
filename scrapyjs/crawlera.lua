
function parse_viewport(viewport)
    -- Splash lua has no regex support, if added, /\d+x\d+/
    local sep = viewport:find("x")
    if sep then
        width = tonumber(viewport:sub(1, sep-1))
        height = tonumber(viewport:sub(sep+1, #viewport))
        if width and height then
            return {width, height}
        end
    end
    return nil
end

function main(splash)
    local args = splash.args
    local crawlera = args.crawlera or {}
    local host = crawlera.host or 'proxy.crawlera.com'
    local port = crawlera.port or 8010
    local subrequest_headers = crawlera.subrequest_headers or {}
    local allrequest_headers = crawlera.headers or {}
    local firstrequest_headers = args.headers or {}

    local session_header = "X-Crawlera-Session"
    local session_id = "create"

    splash:on_request(function (request)
        if session_id ~= 'create' then
            -- Set subresource request headers
            for key,value in pairs(subrequest_headers) do
                request:set_header(name, value)
            end
        end
        for key,value in pairs(allrequest_headers) do
            request:set_header(name, value)
        end

        -- Implement resource_timeout parameter like in render.html
        if type(args.resource_timeout) == 'number' then
            request:set_timeout(args.resource_timeout)
        end

        request:set_header(session_header, session_id)
        request:set_proxy{host, port, username=crawlera.user, password=crawlera.pass}
    end)

    splash:on_response_headers(function (response)
        if type(response.headers[session_header]) ~= nil then
            session_id = response.headers[session_header]
        end
    end)

    -- Implement some of the arguments to render.html

    splash:set_custom_headers(firstrequest_headers)

    if type(args.viewport) == 'string' then
        local width, height = parse_viewport(args.viewport)
        if width and height then
            splash:set_viewport_size(width, height)
        end
    end

    assert(splash:go{args.url, baseurl=args.baseurl, headers=args.headers})

    if args.viewport == 'full' or args.render_all then
        splash:set_viewport_full()
    end

    if type(args.wait) == 'number' then
        splash:wait(args.wait)
    end

    if type(args.js_source) == 'string' then
        splash:runjs(args.js_source)
    end

    return splash:html()
end
