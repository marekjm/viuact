(module A_module (
                  ; Hello, this is a module comment. Nice to meet you.
    (
     let f (ziom) {
                            ; Greetings! I am a function comment. A pleasure to
                            ; meet you.
        (  let msg (struct))
        (         :=   msg
              .
       response
                                        "no elo\n"
                                     )
        (:= msg.sender (Std
                         .Actor.self))
        (
                Std.
          Actor                                                            .send
          ziom
                 msg  )
}
    )
)                                                          )


(
 let      main  (
            )
            {
     (
        let
           x
             ( vector )
             )

     (if ( Std.Vector.size    x  )
       {
            -3
        }
        {
            (   let n  
                 "Hello World!"
                   )
            (
                 print
                   n
                )
        }
0
        )

(
                                            let
                     d
     (
                                try
                         {
           (                             print "no elo"   )
             (   let 
                port
                      16547
                       )
                  (Std.Posix.Network.socket   "127.0.0.1" port
                                 )
         }
            (
  ; I wonder how this will be indented.
               (
catch
Exception_tag
  _
(
print
"oh noes"
)
             )
               (
                 catch      Another_exception_tag name_it
                  {
                    (
                      Std
                      .Actor
                        .send
                          name_it
                           )
                        ( print              name_it
                                              )
                                      }
                )
)
                                                                               )
       )
 }

)
