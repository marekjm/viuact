(module A_module (
    (
     let f (ziom) {
        (  let msg (struct))
        (         :=   msg
              .
       response
                                        "no elo"
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
