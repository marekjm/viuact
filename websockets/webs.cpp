#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

#include <atomic>
#include <chrono>
#include <iostream>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

#include <libwebsockets.h>


std::queue<std::string> from_client;
std::mutex from_client_mtx;

std::queue<std::string> to_client;
std::mutex to_client_mtx;

std::atomic_bool done_with_demo = false;


#define LWS_PLUGIN_STATIC
#include "protocol_lws_minimal_server_echo.cpp"

static lws_protocols protocols[] = {
      LWS_PLUGIN_PROTOCOL_MINIMAL_SERVER_ECHO
    , { nullptr, nullptr, 0, 0 }
};

auto interrupted = int{0};
auto options = int{0};

static lws_protocol_vhost_options const pvo_options = {
      nullptr
    , nullptr
    , "options"
    , reinterpret_cast<char const*>(&options)
};

static lws_protocol_vhost_options const pvo_interrupted = {
      &pvo_options
    , nullptr
    , "interrupted"
    , reinterpret_cast<char const*>(&interrupted)
};

static lws_protocol_vhost_options const pvo = {
      nullptr
    , &pvo_interrupted
    , "lws-minimal-server-echo"
    , ""
};

static lws_extension const extensions[] = {
    {
          "permessage-deflate"
        , lws_extension_callback_pm_deflate
        , "permessage-deflate"
          "; client_no_context_takeover"
          "; client_max_window_bits"
    }
    , { nullptr, nullptr, nullptr }
};

auto sigint_handler(int const sig) -> void {
    interrupted = 1;
}


auto main(int argc, char const** argv) -> int {
    signal(SIGINT, sigint_handler);

    {
        auto logs = int{LLL_USER | LLL_ERR | LLL_WARN | LLL_NOTICE};
        if (auto p = lws_cmdline_option(argc, argv, "-p"); p) {
            logs = atoi(p);
        }
        lws_set_log_level(logs, nullptr);
        lwsl_user("LWS minimal ws client echo + permessage-deflate + multifragment bulk message\n");
        lwsl_user("    lws-minimal-ws-client-echo [-n (no exts)] [-p <port>] [-o (once)]\n");
    }

    auto port = uint16_t{};
    if (auto p = lws_cmdline_option(argc, argv, "-p"); p) {
        port = atoi(p);
    }

    auto options = int{0};
    if (lws_cmdline_option(argc, argv, "-o")) {
        options |= 1;
    }

    lws_context_creation_info info;
    {
        memset(&info, 0, sizeof(info));
        info.port = port;
        info.protocols = protocols;
        info.pvo = &pvo;
        if (!lws_cmdline_option(argc, argv, "-n")) {
            info.extensions = extensions;
        }
        info.pt_serv_buf_size = 32 * 1024;
        info.options = LWS_SERVER_OPTION_VALIDATE_UTF8
            | LWS_SERVER_OPTION_HTTP_HEADERS_SECURITY_BEST_PRACTICES_ENFORCE;
    }

    lws_context* context = lws_create_context(&info);
    if (!context) {
        std::cerr << "lws init failed\n";
        return 1;
    }

    std::thread websocket_runner{[&context]() -> void {
        auto n = int{0};
        while (n >= 0 && !interrupted) {
            n = lws_service(context, 1000);
        }
    }};
    std::thread message_printer{[]() -> void {
        std::this_thread::sleep_for(std::chrono::milliseconds{25});
        std::lock_guard<std::mutex> lck{from_client_mtx};
        if (not from_client.empty()) {
            auto const message = std::move(from_client.front());
            from_client.pop();
            std::cerr << ("> " + message + "\n");
        }
    }};

    while (true) {
        std::string line;
        std::cout << ": ";
        std::getline(std::cin, line);

        if (not line.size()) {
            break;
        }

        std::lock_guard<std::mutex> lck{to_client_mtx};
        to_client.push(std::move(line));
        lws_callback_on_writable_all_protocol(context, protocols);
    }

    websocket_runner.join();
    done_with_demo = true;
    message_printer.join();

    lws_context_destroy(context);

    std::cerr << "exiting: " << (interrupted == 2 ? "ok" : "failed") << '\n';

    return (interrupted != 2);
}
